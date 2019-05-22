# This file contains objects which represent Sacred/Mongo database entries at different levels of abstraction. 
# A SacredConnection must be created externally, it will load all other objects on demand.
# Note that lazy loading is important since Mongo databases can be quite large.
#
# The main idea is that only basic information ('skeleton') is initialized when an object is created:
# For example, when a SacredStudy (the main data container) is created, only the name and 
# identifier are stored in the object (and the object is put into the respective list of SacredDatabase).
# Only when the collection is properly LOADED (or reloaded), SacredExperiment objects are created.
# Again, these initially only store their config field (i.e. what's shown in the overview), not concrete content.
# Load can be called multiple times on an existing object (to reload, of course).
# Note that each object's affiliation to a list must be handled by the PARENT.
#
# Each object must have a parent, to ensure that no memory is leaked.
# 
# Each object emits signals to indicate internal changes. The idea is to keep the required updates
# minimal, also to avoid losing the user selection etc... Unfortunately this is not quite trivial.
# Sometimes a change needs to be signalled in multiple steps.

from . import BrowserState 
from . import Utilities

from PyQt5 import QtCore

import pymongo
import time
import enum
import re
import collections
import gridfs
# 
# # TODO REMOVE
ChangeType = Utilities.ChangeType
ChangeData = Utilities.ChangeData

# Database connection timeout (ms)
DbTimeout = 10000

# These classes are used to signal data changes to the model. The info parameter should be
# - None in the case of Reset
# - the changed rows in the case of Content
# - (position, count) in the case of insert (insert happens BEFORE position, position == len(fields before insert)
#   means that insert was performed at the end
# - (position, count) in the case of delete (position is the first row deleted)

# Helper functions for experiments
def parse_config(cfgDict):
    def recursively_flatten_dict(prefix,dct):
        result = {}
        for key,val in dct.items():
            this_prefix = prefix + '.' + key if prefix != '' else key
            if type(val) is dict:
                result.update(recursively_flatten_dict(this_prefix,val))
            else:
                result[this_prefix] = val
        return result
  
    return recursively_flatten_dict('',cfgDict)

def parse_result(result):
    def parse_list(l):
        if len(l) < 10:
            template = 'Result %d'
        else:
            template = 'Result %02d'
        return { template % pos: val for pos,val in enumerate(l) }

    if type(result) is list:
        result_dict = parse_list(result)
    elif type(result) is dict:
        # have observed different types
        if 'py/tuple' in result:
            result_dict = parse_list(result['py/tuple'])
        else:
            result_dict = { 'Result %s' % k:v for k,v in result.items() } # TODO?
    else:
        print('Cannot interpret result of type',type(result))
        result_dict = {}

    return result_dict

# Abstract parent class for any database entry. Can be loaded and reloaded
# in two parts: load_skeleton (re)loads the skeleton part of the object, load_full loads 
# everything. is_initialized() detects whether the full data has been loaded.
# 
# Whenever an object is reloaded, it must call load_skeleton for all children - this assures
# that information about invalid data is passed down. This should be equivalent to reinitializing
# the child. Also, if load_skeleton detects a change in the underlying data, it should 
# set the initialization flag to False (in a way to avoid memory holes).
#
# All this functionality must be implemented in the subclasses!
#
# Most objects keep their children in an ObjectHolder, which implements common useful
# functionality. Objects should (often via the ObjectHolder) emit suitable signals
# whenever their content has changed.
class AbstractDbEntry(QtCore.QObject):

    ############### General interface ###############
    # Constructor. Note that after the constructor call, load_skeleton should be called.
    def __init__(self,parent):
        super().__init__(parent)
        self._init_timestamp = time.time()
        self._load_timestamp = None

    def name(self):
        pass

    def id(self):
        pass

    def qualified_id(self):
        try:
            parent_id = self.parent().qualified_id() + '-'
        except AttributeError:
            parent_id = ''

        clean_parent_id = parent_id.replace('/','')

        return clean_parent_id + str(self.id()) # TODO maybe id should always return a name

    def typename(self):
        return type(self).__name__

    ############### Loaders ###############
    def load_skeleton(self):
        raise Exception('This function must not be called directly')

    def load_full(self):
        raise Exception('This function must not be called directly')

    def is_initialized(self):
        return self._load_timestamp is not None

    def load_if_uninitialized(self):
        if not self.is_initialized():
            self.load_full()

    def delete(self):
        # debug
        print('Deleting object with id',self.qualified_id())
        self.deleteLater()

# Singleton connection object, main functionality: connect().
# Holds a list of databases (in an ObjectHolder).
class SacredConnection(AbstractDbEntry):
    singleton = None

    # parameters: self, ChangeData
    databases_to_be_changed = QtCore.pyqtSignal(object,ChangeData)
    databases_changed = QtCore.pyqtSignal(object,ChangeData)
    object_to_be_deleted  = QtCore.pyqtSignal(object)

    ############# General Interface #############
    def __init__(self,parent):
        assert self.singleton is None
        super().__init__(parent)
        self._uri = None
        self._mongo_client = None

        # lazily loaded databases
        pre_change_emit = lambda cd: self.databases_to_be_changed.emit(self,cd)
        post_change_emit = lambda cd: self.databases_changed.emit(self,cd)
        loader = lambda key: SacredDatabase(self,key[1],self)
        deleter = lambda ob: ob.delete()
        self._databases = Utilities.ObjectHolder(pre_change_emit=pre_change_emit,post_change_emit=post_change_emit,loader=loader,deleter=deleter)

        self.singleton = self

        self.load_skeleton()

    def name(self):
        return self._uri 

    def id(self):
        return self._uri 

    def load_skeleton(self):
        pass # this class does not have a skeleton - either there is a connection, or not

    def load_full(self):
        # if the connection is not established, must possibly remove old databases!
        if self._mongo_client is None:
            new_keys = []
        else:
            new_keys = sorted([ (self._uri,x) for x in self._mongo_client.database_names() ])

        self._load_timestamp = time.time()

        self._databases.update(new_keys)

        self._databases.forall(lambda x: x.load_skeleton())

    def delete(self):
        # should not actually happen
        self._databases.update([])

        self.object_to_be_deleted.emit(self)
        super().delete()

    ############# Specific Interface #############
    def connect(self,uri):
        if uri != self._uri:
            self._uri = uri
            if uri != None:
                self._mongo_client = pymongo.mongo_client.MongoClient(uri,socketTimeoutMS=DbTimeout) 
            else:
                self._mongo_client = None
            # TODO error handling!

        # in either case, reload (should never do any harm, except cause a bit of delay)
        self.load_full()

    def get_mongo_client(self):
        return self._mongo_client

    def list_databases(self):
        self.load_if_uninitialized()
        return [x[1] for x in self._databases.list_keys()]

    def get_database(self,name):
        self.load_if_uninitialized()
        return self._databases.get_by_key((self._uri,name))[1]

    def delete_database(self,dbname):
        # first delete the database object, which avoids dangling references
        keylist = self._databases.list_keys()
        dbidx = keylist.index((self._uri,dbname))
        del keylist[dbidx]
        self._databases.update(keylist)
        
        # now delete database
        self._mongo_client.drop_database(dbname)
#         self.load_full()

# Sacred database, which holds a) studies and b) filesystems. Only the studies are collected in an ObjectHolder, the filesystems
# are handled ad-hoc. Note that a study can be distributed over several collections (depends on the sacred version).
class SacredDatabase(AbstractDbEntry):

    # parameters: self, ChangeData
    studies_to_be_changed = QtCore.pyqtSignal(object,ChangeData)
    studies_changed = QtCore.pyqtSignal(object,ChangeData)
    object_to_be_deleted  = QtCore.pyqtSignal(object)

    ############# General Interface #############
    def __init__(self,connection,dbname,parent): # always parent == connection TODO also elsewhere?
        super().__init__(parent)
        # immutable properties
        self._connection = connection
        self._dbname = dbname

        self._mongo_database = self._connection.get_mongo_client()[dbname]
        self._filesystems = {} 
        # indexed by "root collection", e.g. "fs". These do not need to be manged by ObjectHolder

        pre_change_emit = lambda cd: self.studies_to_be_changed.emit(self,cd)
        post_change_emit = lambda cd: self.studies_changed.emit(self,cd)
        loader = lambda key: SacredStudy(self,*(self._get_study_info(key)),self)
        deleter = lambda ob: ob.delete()
        self._studies = Utilities.ObjectHolder(pre_change_emit=pre_change_emit,post_change_emit=post_change_emit,loader=loader,deleter=deleter)

        # contains the current assignment of study names to underlying collections - necessary for the
        # loader to work
        self._study_info_dict = {}
        
        self.load_skeleton()

    def name(self):
        return self._dbname

    def id(self):
        return self._dbname

    def load_skeleton(self):
        pass # no skeleton

    def load_full(self):
        # Prepare the assignment of mongo collections to studies
        self._load_study_info()

        new_keys = sorted(self._study_info_dict.keys())

        self._load_timestamp = time.time()

        self._studies.update(new_keys)

        self._studies.forall(lambda x: x.load_skeleton())

        for fs in self._filesystems.values():
            fs.load_skeleton()

    def delete(self):
        self._studies.update([])

        if self._filesystems is not None:
            # don't think we need to emit anything here
            # if so, better use object holder
            fs_keys = list(self._filesystems.keys())
            for k in fs_keys:
                f = self._filesystems[k]
                f.delete()
                del self._filesystems[k]

        # delete this object
        self.object_to_be_deleted.emit(self)
        super().delete()

    ############# Specific Interface #############
    # The database manages the assignment of study names to the underlying collections, as a proxy for
    # the object holder.
    def _load_study_info(self):
        new_collections = list(self._mongo_database.collection_names())
        study_info_list = self._get_study_info_from_collection_names(new_collections)
        self._study_info_dict = { x[0]: x for x in study_info_list }

    def _get_study_info(self,name):
        return self._study_info_dict[name]

    def get_connection(self):
        return self._connection

    def get_mongo_database(self):
        return self._mongo_database

    def list_studies(self):
        self.load_if_uninitialized()
        return self._studies.list_keys()

    def get_study(self,name):
        self.load_if_uninitialized()
        return self._studies.get_by_key(name)[1]

    def get_filesystem(self,root_collection):
        if root_collection in self._filesystems:
            return self._filesystems[root_collection]
        else:
            new_filesystem = SacredFileSystem(self,root_collection)
            self._filesystems[root_collection] = new_filesystem
            return new_filesystem

    def delete_filesystem(self,root_collection):
        fs = self.get_filesystem(root_collection)
        del self._filesystems[root_collection]
        fs.delete_filesystem()

    def delete_study(self,study_name):
        study = self.get_study(study_name)

        # first delete the studies object, which avoids dangling references
        keylist = self._studies.list_keys()
        sidx = keylist.index(study_name)
        del keylist[sidx]
        self._studies.update(keylist)
        
        # now delete study
# # # # # # #         self._mongo_client.drop_database(dbname)
        study._mongo_runs_collection.drop()
        if study._filesystem is not None and not study._grid_fs_shared:
            self.delete_filesystem(study._grid_root)
#         self.load_full()
#         # caution - this deletes the entire study (i.e. the runs collection) from the database
#         # caller should reload the database afterwards
#         study = self.get_study(study_name)
#         print('Now deleting study with qual id',study.qualified_id())
#         study._mongo_runs_collection.drop()
#         if study._filesystem is not None and not study._grid_fs_shared:
#             self.delete_filesystem(study._grid_root)
# 
#         study.delete()
# 
#         self.load_full() # reload and propagate


    ############# Internals #############
    @staticmethod
    def _get_study_info_from_collection_names(cn):
        study_info = [] # name, runs_collection, gridfs_root, gridfs_is_shared
        # step 1
        if 'experiments' in cn:
            cn.remove('experiments')
            study_info.append(('(experiments)','experiments',None,None))

        # step 2
        runs_collections = [ x for x in cn if x.endswith('runs') ]
        for rc in runs_collections:
            base_name = re.sub('runs$','',rc)
            visible_name = base_name.rstrip('.') if base_name != '' else '(default)'
            if (base_name + 'files') in cn and (base_name + 'chunks') in cn:
                study_info.append( (visible_name,base_name + 'runs',base_name.rstrip('.'),False) )

            else:
                if 'fs.files' in cn and 'fs.chunks' in cn:
                    study_info.append((visible_name,base_name + 'runs','fs',True))
                else:
                    study_info.append((visible_name,base_name + 'runs',None,None))

        to_remove = [ x for x in cn if (re.match(r'.*\.files$',x) and x != 'fs.files') or (re.match(r'.*\.chunks$',x) and x != 'fs.chunks') or re.match(r'.*runs$',x) ]
        for r in to_remove:
            cn.remove(r)

        # step 3
        if 'fs.files' in cn and 'fs.chunks' in cn:
            # remaining dbs, except system.indices, are run dbs
            for x in cn:
                if x not in [ 'system.indexes','fs.files','fs.chunks' ]:
                    study_info.append((x,x,'fs',True))

            to_remove = [ 'fs.files','fs.chunks' ]
            for r in to_remove:
                cn.remove(r)

        return study_info

# A single sacred study, consisting of experiments. A study may be distributed over several collections in various ways!
class SacredStudy(AbstractDbEntry):
    experiments_to_be_changed = QtCore.pyqtSignal(object,ChangeData)
    experiments_changed = QtCore.pyqtSignal(object,ChangeData)
    object_to_be_deleted  = QtCore.pyqtSignal(object)

    ############# General Interface #############
    def __init__(self,database,name,runs_name,grid_root,grid_fs_shared,parent):
        super().__init__(parent)
        self._database = database
        self._name = name
        self._runs_name = runs_name
        self._grid_root = grid_root
        self._grid_fs_shared = grid_fs_shared

        self._mongo_runs_collection = self._database.get_mongo_database()[self._runs_name]
        self._filesystem = None

        # lazily loaded experiments
        self._filter = {}
        pre_change_emit = lambda cd: self.experiments_to_be_changed.emit(self,cd)
        post_change_emit = lambda cd: self.experiments_changed.emit(self,cd)
        loader = lambda obid: SacredExperiment(self,obid,self)
        deleter = lambda ob: ob.delete()
        self._experiments = Utilities.ObjectHolder(pre_change_emit=pre_change_emit,post_change_emit=post_change_emit,loader=loader,deleter=deleter)

        self.load_skeleton()

    def name(self):
        return self._name

    def id(self):
        return self._name

    def load_skeleton(self):
        pass # no skeleton

    def load_full(self):
#         print('---> Call to SacredStudy.load_full, active filter',self._filter)
        new_experiments = self._mongo_runs_collection.find(self._filter,projection={'_id': 1})
        new_keys = sorted([x['_id'] for x in new_experiments if '_id' in x and x['_id'] is not None])

        self._load_timestamp = time.time()

        self._experiments.update(new_keys)

        self._experiments.forall(lambda x: x.load_skeleton())

        # obtain GRIDFS file system
        if self._grid_root is not None:
            self._filesystem = self._database.get_filesystem(self._grid_root) # will not load filesystem twice

    def delete(self):
        # delete children automatically
        self._experiments.update([])

        # delete this object
        self.object_to_be_deleted.emit(self)
        super().delete()

    ############# Specific Interface #############
    def set_filter(self,flt):
        self._filter = flt
        # note: caller must call load_full!

    def get_database(self):
        return self._database

    def list_experiments(self):
        self.load_if_uninitialized()
#         return sorted(self._experiments.keys()) # but note that the sorting is given by the sort order
        return self._experiments.list_keys()

    def get_experiment(self,obid):
        self.load_if_uninitialized()
        return self._experiments.get_by_key(obid)

    def get_all_experiments(self):
        self.load_if_uninitialized()
        return [self._experiments.get_by_key(obid)[1] for obid in self._experiments.list_keys()]

    def load_experiment_data(self,obid,projection=None):
        # returns a dictionary
        find_result = self._mongo_runs_collection.find({'_id': obid},projection=projection)
        # TODO error handling, TODO move to interior of experiment?
        return next(iter(find_result))

    def list_fields(self):
        return self.list_config_fields() + self.list_result_fields()

    def list_config_fields(self):
        self.load_if_uninitialized()
        all_config_fields = set() 
        for exp in self._experiments.list_values():
            all_config_fields |= set(exp.get_config_fields())
        return sorted(all_config_fields)

    def list_result_fields(self):
        self.load_if_uninitialized()
        all_result_fields = set() 
        for exp in self._experiments.list_values():
            all_result_fields |= set(exp.get_result_fields())
        return sorted(all_result_fields)

    def delete_experiments_from_database(self,exp_ids):
        assert type(exp_ids) is set
        query_dict = { '$or': [ { '_id': i } for i in exp_ids ] }
        res = self._mongo_runs_collection.remove(query_dict)
        # res - {'ok': 1, 'n': 2}
        # TODO interpret, report error if there was one
# # #         self.load()
        # note: caller MUST reload 
        
    def get_filesystem(self):
        return self._filesystem



# A single experiment, corresponding to a single run of a sacred script. Relies on parent study in order to load its data.
class SacredExperiment(AbstractDbEntry):
    experiment_to_be_changed = QtCore.pyqtSignal()
    experiment_changed = QtCore.pyqtSignal()
    object_to_be_deleted = QtCore.pyqtSignal()

    ############# General Interface #############

    def __init__(self,study,obid,parent):
        super().__init__(parent)
        self._study = study
        self._obid = obid

#         # load initial data
#         exp_dict = self._study.load_experiment_data(self._obid,projection={'_id': 1, 'config': 1, 'result': 1, 'status': 1})
#         if 'result' in exp_dict:
#             result_dict = parse_result(exp_dict['result'])
#         else:
#             result_dict = {}
# 
#         if 'config' in exp_dict:
#             config_dict = parse_config(exp_dict['config'])
#         else:
#             config_dict = {}
# 
#         status = exp_dict['status'] if 'status' in exp_dict else 'UNKNOWN'
# 
#         self._config = config_dict
#         self._result = result_dict
#         self._status = status 
#         self._details = None # loaded only when necessary, may really be large
#         self._experiment_data = None # only loaded if necessary

        # invalid, call load_skeleton
        self._config = None
        self._result = None
        self._status = None
        self._details = None 
        self._experiment_data = None 
        self._heartbeat_timestamp = None

        self.load_skeleton()

    def name(self):
        return 'Experiment_' + str(self._obid)

    def id(self):
        return self._obid

    def load_skeleton(self):
# #         print('Loading experiment skeleton for obid',self._obid)
        exp_dict = self._study.load_experiment_data(self._obid,projection={'_id': 1, 'config': 1, 'result': 1, 'status': 1, 'heartbeat': 1})
        if 'result' in exp_dict:
            result_dict = parse_result(exp_dict['result'])
        else:
            result_dict = {}

        if 'config' in exp_dict:
            config_dict = parse_config(exp_dict['config'])
        else:
            config_dict = {}

        status = exp_dict['status'] if 'status' in exp_dict else 'UNKNOWN'

        self._config = config_dict
        self._result = result_dict
        self._status = status 

        # finally check whether the heartbeat is new, ugly conditional partly for debugging
        if 'heartbeat' in exp_dict:
            current_heartbeat = exp_dict['heartbeat'] # should be datetime
            if current_heartbeat is not None:
                if self._heartbeat_timestamp is None:
                    pass
#                     print('IIIIIIIIIIIIINITIALIZING heartbeat')
                elif self._heartbeat_timestamp < current_heartbeat:
#                     print('NNNNNNNEEEEEEEEEEEWWWWWWWWWWWW obid',self._obid)
                    self._load_timestamp = None # mark as NOT current, next call to load_if_uninitialized will reload
                else:
                    pass
#                     print('-----------NOCHANGE')
            self._heartbeat_timestamp = current_heartbeat

    def load_full(self):
        print('Loading full experiment for obid',self._obid)
        self.experiment_to_be_changed.emit()

        self._details = self._study.load_experiment_data(self._obid)
        self._config = parse_config(self._details['config']) if 'config' in self._details else {}
        self._result = parse_result(self._details['result']) if 'result' in self._details else {}

        self._load_timestamp = time.time()
        self.experiment_changed.emit()

    def delete(self):
        self.object_to_be_deleted.emit()
        super().delete()


    ############# Specific Interface #############

    def get_experiment_data(self):
        self.load_if_uninitialized()
        return self._experiment_data

    def get_config_fields(self):
        return sorted(self._config.keys())

    def get_result_fields(self):
        return sorted(self._result.keys())

    def get_field(self,fieldname):
        if fieldname[0] == BrowserState.Fields.FieldType.Config:
            return self._config[fieldname[1]] if fieldname[1] in self._config else '---'
        elif fieldname[0] == BrowserState.Fields.FieldType.Result:
            return self._result[fieldname[1]] if fieldname[1] in self._result else '---'
        else:
            raise KeyError('Field %s not found' % fieldname)

    def get_status(self):
        return self._status

    def get_details(self):
        self.load_if_uninitialized()
        return self._details

    def get_study(self):
        return self._study

class SacredFileSystem(AbstractDbEntry):
    # These are called from load()
    # TODO do we need that?
    fs_to_be_changed = QtCore.pyqtSignal()
    fs_changed = QtCore.pyqtSignal()
    object_to_be_deleted = QtCore.pyqtSignal()

    ############# General Interface #############

    def __init__(self,parent,root_collection):
        super().__init__(parent)
        self._parent = parent
        self._root_collection = root_collection
        self._grid_fs = gridfs.GridFS(self._parent.get_mongo_database(),root_collection)
        print('CREATED NEW FILESYSTEM',root_collection,' and list of files is',self.list())

    def name(self):
        return self._root_collection

    def id(self):
        return self._root_collection

    def load_skeleton(self):
        pass

    def load_full(self):
        pass

    def delete(self):
        self.object_to_be_deleted.emit()
        super().delete()

    ############# Specific Interface #############

    # Get all SOURCE files belonging to some experiment
    # all TODO
    def get_file(self,name):
        data = self._grid_fs.find_one({'filename': name}).read()
        return data

    def list(self):
        return self._grid_fs.list()

    # delete filesystem from database, assumes that parent SacredDatabase object also deletes link to this object
    def delete_filesystem(self):
        # assume this is ok, delete files and chunks
        files_name = self._root_collection + '.files'
        chunks_name = self._root_collection + '.chunks'
        files_collection = self._parent.get_mongo_database()[files_name]
        chunks_collection = self._parent.get_mongo_database()[chunks_name]

        files_collection.drop()
        chunks_collection.drop()


if __name__ == '__main__':
    from PyQt5 import QtGui, QtWidgets
    import numpy as np

    def pick_any(iterable):
        data = list(iterable)
        which_one = np.random.choice(len(data))
        return data[which_one]

    class TestApplication(QtWidgets.QApplication):
        def __init__(self):
            super().__init__([])

            # make sacred connection
            connection = SacredConnection('mongodb://localhost:27017',self)
            connection.load_full()
            database = connection.get_database(pick_any(connection.list_databases()))
            database.load_full()
            collection = database.get_study(pick_any(database.list_studies()))
            collection.load_full()

            # make window
            self.win = QtWidgets.QWidget()

            self.treeview = QtWidgets.QTreeView()

            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(self.treeview)
            self.win.setLayout(layout)
            self.win.show()

            # make model (only databases) and go
            self.model = QtGui.QStandardItemModel()
            parent_item = self.model.invisibleRootItem()
            for dbname in connection.list_databases():
                new_item = QtGui.QStandardItem(dbname)
                new_item.setData(connection.get_database(dbname),QtCore.Qt.UserRole + 1)
                parent_item.appendRow(new_item)
            
            self.model.setHorizontalHeaderLabels(['UNINITIALIZED HEADER'])

            self.treeview.setModel(self.model)
            self.treeview.selectionModel().selectionChanged.connect(self.slot_selection_changed)


        def slot_selection_changed(self):
            selected_indexes = self.treeview.selectionModel().selectedIndexes()
            assert len(selected_indexes) <= 1
            if len(selected_indexes) == 0:
                return
            else:
                model_item = self.model.itemFromIndex(selected_indexes[0])
                sacred_item = self.get_associated_sacred_item(model_item)

                # possibly augment model!
                if type(sacred_item) is SacredDatabase:
                    if not sacred_item.is_initialized():
                        sacred_item.load_full()
                        for collname in sacred_item.list_studies():
                            new_item = QtGui.QStandardItem(collname)
                            new_item.setData(sacred_item.get_study(collname),QtCore.Qt.UserRole + 1)
                            model_item.appendRow(new_item)

                elif type(sacred_item) is SacredStudy:
                    if not sacred_item.is_initialized():
                        sacred_item.load_full()
                        for expname in sacred_item.list_experiments():
                            new_item = QtGui.QStandardItem(str(expname))
                            new_item.setData(sacred_item.get_experiment(expname),QtCore.Qt.UserRole + 1)
                            model_item.appendRow(new_item)

                elif type(sacred_item) is SacredExperiment:
                    if not sacred_item.is_initialized():
                        sacred_item.load_full()


        def get_associated_sacred_item(self,model_item):
            return model_item.data(QtCore.Qt.UserRole + 1) # that works?


    app = TestApplication()
    QtCore.pyqtRemoveInputHook()
    app.exec_()
