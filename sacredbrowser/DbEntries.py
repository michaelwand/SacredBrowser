# This file contains objects which represent Sacred/Mongo database entries at different levels of abstraction. 
# A SacredConnection must be created externally, it will load all other objects on demand.
# Note that lazy loading is important since Mongo databases can be quite large.
#
# Each object must have a parent, to ensure that no memory is leaked.
# 
# Each object emits signals to indicate internal changes. The idea is to keep the required updates
# minimal, also to avoid losing the user selection etc... Unfortunately this is not quite trivial.
# Sometimes a change needs to be signalled in multiple steps.

from . import BrowserState 

from PyQt5 import QtCore

import pymongo
import time
import enum
import re
import collections
import gridfs

# Database connection timeout (ms)
DbTimeout = 10000

# These classes are used to signal data changes to the model. The info parameter should be
# - None in the case of Reset
# - the changed rows in the case of Content
# - (position, count) in the case of insert (insert happens BEFORE position, position == len(fields before insert)
#   means that insert was performed at the end
# - (position, count) in the case of delete (position is the first row deleted)

class ChangeType(enum.Enum):
    Reset = 1
    Content = 2
    Insert = 3
    Remove = 4
ChangeData = collections.namedtuple('ChangeData',['tp','info'])

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

# ok, so the idea is that only basic information is initialized when an object is created:
# For example, when a SacredStudy is created (this may refer to more than one mongo collection, BTW),
# only the name and identifier are stored in the object (and the object is put into the respective list).
# Only when the collection is properly LOADED (or reloaded), SacredExperiment objects are created, 
# again these only store their config field (i.e. what's shown in the overview), not concrete content.
# Load can be called multiple times on an existing object (to reload, of course).
#
# Note that no object puts itself in the list of objects (that's the responsibility of the "parent"),
# possibly excepting the singleton SacredConnection
class AbstractDbEntry(QtCore.QObject):

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

        return clean_parent_id + self.id()

    def typename(self):
        return type(self).__name__

    def is_initialized(self):
        return self._load_timestamp is not None

    def load_if_uninitialized(self):
        if self._load_timestamp is None:
            self.load()

    def load(self):
        pass

class SacredConnection(AbstractDbEntry):
    singleton = None

    # parameters: self, ChangeData
    databases_to_be_changed = QtCore.pyqtSignal(object,ChangeData)
    databases_changed = QtCore.pyqtSignal(object,ChangeData)

    ############# General Interface #############
    def __init__(self,parent):
        assert self.singleton is None
        super().__init__(parent)
        self._uri = None
        self._mongo_client = None

        # Lazily loaded. _databases is a dictionary (db id -> SacredDatabase), where db id is a pair 
        # (uri, dbname) - thus there is no confusion between different mongo clients.
        self._databases = {}
        self._sorted_database_keys = []

        self.singleton = self

    def name(self):
        return self._uri 

    def id(self):
        return self._uri 

    def load(self):
        # if the connection is not established, must possibly remove old databases!
        if self._mongo_client is None:
            new_keys = []
        else:
            new_keys = [ (self._uri,x) for x in self._mongo_client.database_names() ]

        # Remove deleted databases (TODO test) - note that all prior databases are removed if uri changes.
        if self._databases is not None:
            to_be_removed = set(self._sorted_database_keys) - set(new_keys)

            for k in to_be_removed:
                pos= self._sorted_database_keys.index(k)
                db = self._databases[k]
                
                # perform change
                change_data = ChangeData(ChangeType.Remove,(pos,1))
                self.databases_to_be_changed.emit(self,change_data)
                db.deleteLater()
                del self._databases[k]
                del self._sorted_database_keys[pos]
                self.databases_changed.emit(self,change_data)


        # Initialize if necessary
        if self._databases is None:
            self._databases = {}
            self._sorted_database_keys = []

        self._load_timestamp = time.time()

        # Add new keys
        for n in sorted(new_keys):
            if n in self._sorted_database_keys:
                continue # already present
            else:
                change_data = ChangeData(ChangeType.Insert,(len(self._sorted_database_keys),1))
                self.databases_to_be_changed.emit(self,change_data)
                db = SacredDatabase(self,n[1],self)
                self._databases[n] = db
                self._sorted_database_keys.append(n)
                self.databases_changed.emit(self,change_data)

    ############# Specific Interface #############
    def connect(self,uri):
        self._uri = uri
        self._mongo_client = pymongo.mongo_client.MongoClient(uri,socketTimeoutMS=DbTimeout) 
        # TODO error handling!
        self.load()

    def get_mongo_client(self):
        return self._mongo_client

    def list_databases(self):
        self.load_if_uninitialized()
        return [ x[1] for x in self._sorted_database_keys ] # remove URI

    def get_database(self,name):
        self.load_if_uninitialized()
        return self._databases[(self._uri,name)]

#     ############# Internals #############
#     def _delete_children(self):
#         if self._databases is not None:
#             for ob in self._databases.values():
#                 ob.deleteLater()
#         self._databases = None

class SacredDatabase(AbstractDbEntry):

    # parameters: self, ChangeData
    studies_to_be_changed = QtCore.pyqtSignal(object,ChangeData)
    studies_changed = QtCore.pyqtSignal(object,ChangeData)

    ############# General Interface #############
    def __init__(self,connection,dbname,parent):
        super().__init__(parent)
        self._connection = connection
        self._dbname = dbname

        self._mongo_database = self._connection.get_mongo_client()[dbname]
        self._filesystems = {} # indexed by "root collection", e.g. "fs"

        # lazily loaded
        self._mongo_collection_names = None
        self._studies = None
        self._sorted_study_keys = None

    def name(self):
        return self._dbname

    def id(self):
        return self._dbname

    def load(self):
        print('>>>> Loading database',self._dbname)
        # Load studies, diff lists. Let's try to add new studies at the end, probably easier for user.
        new_collections = list(self._mongo_database.collection_names())
        new_study_info = self._get_study_info_from_collection_names(new_collections)
        new_keys = [x[0] for x in new_study_info]

        # remove deleted studies (TODO test)
        if self._studies is not None:
            to_be_removed = set(self._sorted_study_keys) - set(new_keys)

            for k in to_be_removed:
                pos= self._sorted_study_keys.index(k)
                st = self._studies[k]
                
                # perform change
                change_data = ChangeData(ChangeType.Remove,(pos,1))
                self.studies_to_be_changed.emit(self,change_data)
                st.deleteLater()
                del self._studies[k]
                del self._sorted_study_keys[pos]
                self.studies_changed.emit(self,change_data)


        # Initialize if necessary
        if self._studies is None:
            self._studies = {}
            self._sorted_study_keys = []

        self._load_timestamp = time.time()

        # Add new keys
        for si in sorted(new_study_info):
            if si[0] in self._sorted_study_keys:
                continue # already present
            else:
                change_data = ChangeData(ChangeType.Insert,(len(self._sorted_study_keys),1))
                self.studies_to_be_changed.emit(self,change_data)
                study = SacredStudy(self,*si,self)
                self._studies[si[0]] = study
                self._sorted_study_keys.append(si[0])
                self.studies_changed.emit(self,change_data)


    ############# Specific Interface #############
    def get_connection(self):
        return self._connection

    def get_mongo_database(self):
        return self._mongo_database

    def list_studies(self):
        return self._sorted_study_keys

    def get_study(self,name):
        self.load_if_uninitialized()
        return self._studies[name]

    def get_filesystem(self,root_collection):
        if root_collection in self._filesystems:
            return self._filesystems[root_collection]
        else:
            new_filesystem = SacredFileSystem(self,root_collection)
            self._filesystems[root_collection] = new_filesystem
            return new_filesystem


    ############# Internals #############
    @staticmethod
    def _get_study_info_from_collection_names(cn):
        study_info = [] # name, runs_collection, gridfs_root
        # step 1
        if 'experiments' in cn:
            cn.remove('experiments')
            study_info.append(('(experiments)','experiments',None))

        # step 2
        runs_collections = [ x for x in cn if x.endswith('runs') ]
        for rc in runs_collections:
            base_name = re.sub('runs$','',rc)
            visible_name = base_name.rstrip('.') if base_name != '' else '(default)'
            if (base_name + 'files') in cn and (base_name + 'chunks') in cn:
                study_info.append((visible_name,base_name + 'runs',base_name.rstrip('.')))

            else:
                if 'fs.files' in cn and 'fs.chunks' in cn:
                    study_info.append((visible_name,base_name + 'runs','fs'))
                else:
                    study_info.append((visible_name,base_name + 'runs',None))

        to_remove = [ x for x in cn if (re.match(r'.*\.files$',x) and x != 'fs.files') or (re.match(r'.*\.chunks$',x) and x != 'fs.chunks') or re.match(r'.*runs$',x) ]
        for r in to_remove:
            cn.remove(r)

        # step 3
        if 'fs.files' in cn and 'fs.chunks' in cn:
            # remaining dbs, except system.indices, are run dbs
            for x in cn:
                if x not in [ 'system.indexes','fs.files','fs.chunks' ]:
                    study_info.append((x,x,'fs'))

            to_remove = [ 'fs.files','fs.chunks' ]
            for r in to_remove:
                cn.remove(r)

        return study_info


class SacredStudy(AbstractDbEntry):
    experiments_to_be_reset = QtCore.pyqtSignal(object)
    experiments_reset = QtCore.pyqtSignal(object)

    ############# General Interface #############
    def __init__(self,database,name,runs_name,grid_root,parent):
        super().__init__(parent)
        self._database = database
        self._name = name
        self._runs_name = runs_name
        self._grid_root = grid_root

        self._mongo_runs_collection = self._database.get_mongo_database()[self._runs_name]
        self._filesystem = None

        # lazily loaded
        self._experiments = None

    def name(self):
        return self._name

    def id(self):
        return self._name

    # filter must have mongodb format (see Utilities.py)
    def load(self,filter = {}):

        # (re)load experiments
        self.experiments_to_be_reset.emit(self)

        self._delete_children() # that's crap

        collection_data = self._mongo_runs_collection.find(filter,projection={'_id': 1, 'config': 1, 'result': 1, 'status': 1})
        self._experiments = {}
        for item in collection_data:
            if 'result' in item:
                result_dict = parse_result(item['result'])
            else:
                result_dict = {}

            if 'config' in item:
                config_dict = parse_config(item['config'])
            else:
                config_dict = {}

            status = item['status'] if 'status' in item else 'UNKNOWN'
            self._experiments[item['_id']] = SacredExperiment(self,item['_id'],config_dict,result_dict,status,self)

        # obtain GRIDFS file system
        if self._grid_root is not None:
            self._filesystem = self._database.get_filesystem(self._grid_root)

        self._load_timestamp = time.time()
        self.experiments_reset.emit(self)

    ############# Specific Interface #############
    def get_database(self):
        return self._database

    def list_experiments(self):
        self.load_if_uninitialized()
        return sorted(self._experiments.keys()) # but note that the sorting is given by the sort order

    def get_experiment(self,name):
        self.load_if_uninitialized()
        return self._experiments[name]

    def get_all_experiments(self):
        self.load_if_uninitialized()
        return self._experiments


    def load_experiment_data(self,obid):
        # returns a dictionary
        find_result = self._mongo_runs_collection.find({'_id': obid})
        # TODO error?
        return next(iter(find_result))

    def list_fields(self):
        return self.list_config_fields() + self.list_result_fields()

    def list_config_fields(self):
        self.load_if_uninitialized()
        all_config_fields = set() # TODO cache?
        for exp in self._experiments.values():
            all_config_fields |= set(exp.get_config_fields())
        return sorted(all_config_fields)

    def list_result_fields(self):
        self.load_if_uninitialized()
        all_result_fields = set() # TODO cache?
        for exp in self._experiments.values():
            all_result_fields |= set(exp.get_result_fields())
        return sorted(all_result_fields)

    def delete_experiments_from_database(self,exp_ids):
        assert type(exp_ids) is set
        query_dict = { '$or': [ { '_id': i } for i in exp_ids ] }
        res = self._mongo_runs_collection.remove(query_dict)
        # res - {'ok': 1, 'n': 2}
        # TODO interpret, report error if there was one
# # #         self.load()
        # note: caller MUST reload with valid filter
        
    def get_filesystem(self):
        return self._filesystem

    ############# Internals #############
    def _delete_children(self):
        if self._experiments is not None:
            for ob in self._experiments.values():
                ob.deleteLater()
        self._experiments = None


class SacredExperiment(AbstractDbEntry):
    experiment_to_be_changed = QtCore.pyqtSignal()
    experiment_changed = QtCore.pyqtSignal()

    ############# General Interface #############

    def __init__(self,study,obid,config,result,status,parent):
        super().__init__(parent)
        self._study = study
        self._obid = obid
        self._config = config # a dictionary
        self._result = result # also a dictionary
        self._details = None # loaded only when necessary, may really be large
        self._status = status 
        self._experiment_data = None # only loaded if necessary

    def name(self):
        return 'Experiment_' + str(self._obid)

    def id(self):
        return self._obid

    def load(self):
        self.experiment_to_be_changed.emit()

        self._details = self._study.load_experiment_data(self._obid)
        self._config = parse_config(self._details['config']) if 'config' in self._details else {}
        self._result = parse_result(self._details['result']) if 'result' in self._details else {}

        self._load_timestamp = time.time()
        self.experiment_changed.emit()

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

    ############# General Interface #############

    def __init__(self,parent,root_collection):
        self._parent = parent
        self._root_collection = root_collection
        self._grid_fs = gridfs.GridFS(self._parent.get_mongo_database(),root_collection)
        print('CREATED NEW FILESYSTEM',root_collection,' and list of files is',self.list())

    def name(self):
        return self._root_collection

    def id(self):
        return self._root_collection

    def load(self):
        # TODO
        pass


    ############# Specific Interface #############

    # Get all SOURCE files belonging to some experiment
    # all TODO
    def get_file(self,name):
        data = self._grid_fs.find_one({'filename': name}).read()
        return data

    def list(self):
        return self._grid_fs.list()

#         self.filesModel = QtGui.QStandardItemModel()
#         self.filesList.setModel(self.filesModel)
# 
#         self.filesList.activated.connect(self.slotDisplayPreview)
# 
#         # iterate over entry keys, fill model
#         if self.currentGridFs is not None:
#             # for artifact filenames, filter for id
#             desiredId = entry['_id']
#             # for sources, requires md hash
#             # TODO this assumes that all sources are mentioned, and may fail when sacred changes!!!
#             sourceList = entry['sources']
#             sourceDict = { e[0]: e[1] for e in sourceList }
# 
#             for fn in sorted(self.currentGridFs.list()):
#                 if re.match(r'^artifact://',fn):
#                     (expname,thisId,thisFilename) = re.match(r'^artifact://([^/]*)/([^/]*)/(.*)$',fn).groups()
#                     if str(thisId) != str(desiredId):
#                         continue # this artifact does not belong to this instance
#                     # TODO add error handling?
#                     displayName = 'Artifact: ' + thisFilename
#                     gridSearchCondition = { 'filename': fn } # TODO parse experimententry for artifact info?
#                     origFilename = thisFilename
#                 else:
#                     if fn in sourceDict:
#                         md5Hash = sourceDict[fn] 
#                         displayName = str(fn)
#                         gridSearchCondition = { 'filename': fn, 'md5': md5Hash } 
#                         origFilename = os.path.basename(displayName)
#                     elif os.path.basename(fn) in sourceDict: # TODO FIXME XXX awful hack
#                         shortFn = os.path.basename(fn)
#                         md5Hash = sourceDict[shortFn] 
#                         displayName = str(shortFn)
#                         gridSearchCondition = { 'filename': fn, '_id': md5Hash }  # HACK HERE
#                         origFilename = os.path.basename(displayName)
#                     else:
#                         continue
# 
#                 item = FileItem(displayName,gridSearchCondition,origFilename)
#                 item.setEditable(False)
#                 self.filesModel.appendRow(item)
# 
#             self.previewFileButton.clicked.connect(self._slot_preview_button_clicked)
#             self.saveFileButton.clicked.connect(self._slot_save_button_clicked)
#             self.previewFileButton.setEnabled(True)
#             self.saveFileButton.setEnabled(True)
#         else:
#             self.previewFileButton.setEnabled(False)
#             self.saveFileButton.setEnabled(False)
# 

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
            connection.load()
            database = connection.get_database(pick_any(connection.list_databases()))
            database.load()
            collection = database.get_study(pick_any(database.list_studies()))
            collection.load()

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
            
            self.model.setHorizontalHeaderLabels(['blurp'])

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
                        sacred_item.load()
                        for collname in sacred_item.list_studies():
                            new_item = QtGui.QStandardItem(collname)
                            new_item.setData(sacred_item.get_study(collname),QtCore.Qt.UserRole + 1)
                            model_item.appendRow(new_item)

                elif type(sacred_item) is SacredStudy:
                    if not sacred_item.is_initialized():
                        sacred_item.load()
                        for expname in sacred_item.list_experiments():
                            new_item = QtGui.QStandardItem(str(expname))
                            new_item.setData(sacred_item.get_experiment(expname),QtCore.Qt.UserRole + 1)
                            model_item.appendRow(new_item)

                elif type(sacred_item) is SacredExperiment:
                    if not sacred_item.is_initialized():
                        sacred_item.load()


        def get_associated_sacred_item(self,model_item):
            return model_item.data(QtCore.Qt.UserRole + 1) # that works?


    app = TestApplication()
    QtCore.pyqtRemoveInputHook()
    app.exec_()
