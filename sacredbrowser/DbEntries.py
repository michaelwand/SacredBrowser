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
        return super().qualified_id() + '-' + self.id

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
    def __init__(self,uri,parent):
        assert self.singleton is None
        super().__init__(parent)
        self._uri = uri
        self._mongo_client = pymongo.mongo_client.MongoClient(uri,socketTimeoutMS=50000) 

        # lazily loaded
        self._databases = None
        self._sorted_database_keys = None

        # easily changed
        self.singleton = self

    def name(self):
        return self._uri 

    def id(self):
        return self._uri 

    def load(self):
        # Load databases, diff lists. Let's try to add new databases at the end, probably easier for user.
        new_keys = list(self._mongo_client.database_names())

        # remove deleted databases (TODO test)
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
                db = SacredDatabase(self,n,self)
                self._databases[n] = db
                self._sorted_database_keys.append(n)
                self.databases_changed.emit(self,change_data)

    ############# Specific Interface #############
    def get_mongo_client(self):
        return self._mongo_client

    def list_databases(self):
        self.load_if_uninitialized()
        return self._sorted_database_keys

    def get_database(self,name):
        self.load_if_uninitialized()
        return self._databases[name]

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

        # lazily loaded
        self._mongo_collection_names = None
        self._studies = None
        self._sorted_study_keys = None

    def name(self):
        return self._dbname

    def id(self):
        return self._dbname

    def load(self):
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

    ############# Internals #############
    @staticmethod
    def _get_study_info_from_collection_names(cn):
        study_info = [] # name, runs_collection, gridfs_files, gridfs_chunks
        # step 1
        if 'experiments' in cn:
            cn.remove('experiments')
            study_info.append(('(experiments)','experiments',None,None))

        # step 2
        runs_collections = [ x for x in cn if x.endswith('.runs') ]
        for rc in runs_collections:
            base_name = re.sub('.runs$','',rc)
            if (base_name + '.files') in cn and (base_name + '.chunks') in cn:
                study_info.append((base_name,base_name + '.runs',base_name + '.files',base_name + '.chunks'))

            else:
                study_info.append((base_name,base_name + '.runs',None,None))

        to_remove = [ x for x in cn if (re.match(r'.*\.files$',x) and x != 'fs.files') or (re.match(r'.*\.chunks$',x) and x != 'fs.chunks') or re.match(r'.*\.runs$',x) ]
        for r in to_remove:
            cn.remove(r)

        # step 3
        if 'fs.files' in cn and 'fs.chunks' in cn:
            # remaining dbs, except system.indices, are run dbs
            for x in cn:
                if x != 'system.indexes':
                    study_info.append((x,x,'fs.files','fs.chunks'))

        return study_info


class SacredStudy(AbstractDbEntry):
    experiments_to_be_reset = QtCore.pyqtSignal(object)
    experiments_reset = QtCore.pyqtSignal(object)

    ############# General Interface #############
    def __init__(self,database,name,runs_name,files_name,chunks_name,parent):
        super().__init__(parent)
        self._database = database
        self._name = name
        self._runs_name = runs_name
        self._files_name = files_name
        self._chunks_name = chunks_name

        self._mongo_runs_collection = self._database.get_mongo_database()[self._runs_name]
        self._mongo_files_collection = self._database.get_mongo_database()[self._files_name] if self._files_name is not None else None
        self._mongo_chunks_collection = self._database.get_mongo_database()[self._chunks_name] if self._chunks_name is not None else None

        # lazily loaded
        self._experiments = None

    def name(self):
        return self._name

    def id(self):
        return self._name

    # filter must have mongodb format (see Utilities.py)
    def load(self,filter = {}):
        print('Loading experiment list for study',self.name())
        self.experiments_to_be_reset.emit(self)

        self._delete_children()

        collection_data = self._mongo_runs_collection.find(filter,projection={'_id': 1, 'config': 1, 'result': 1})
        self._experiments = {}
        for item in collection_data:
            if 'result' in item:
                if type(item['result']) is list:
                    if len(item['result']) < 10:
                        template = 'Result %d'
                    else:
                        template = 'Result %02d'
                    result_dict = { template % pos: val for pos,val in enumerate(item['result']) }
                elif type(item['result']) is dict:
                    result_dict = item['result'] # TODO
                else:
                    print('Cannot interpret result of type',type(item['result']))
                    result_dict = {}
            else:
                print('No result...')
                result_dict = {}
            self._experiments[item['_id']] = SacredExperiment(self,item['_id'],item['config'],result_dict,self)
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
        return self._mongo_runs_collection.find({'_id': obid})

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

    ############# Internals #############
    def _delete_children(self):
        if self._experiments is not None:
            for ob in self._experiments.values():
                ob.deleteLater()
        self._experiments = None


class SacredExperiment(AbstractDbEntry):
    def __init__(self,collection,obid,config,result,parent):
        super().__init__(parent)
        self._collection = collection
        self._obid = obid
        self._config = config # a dictionary
        self._result = result # also a dictionary
        self._experiment_data = None # only loaded if necessary

    def name(self):
        return 'Experiment_' + str(self._obid)

    def id(self):
        return self._obid

    def load(self):
        self._experiment_data = self._collection.load_experiment_data(self._obid)
        self._load_timestamp = time.time()
        self.changed.emit()

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
            print('SELECTION CHANGED')
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
