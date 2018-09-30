# This file contains objects which represent models to represent the entries of the
# sacred database entries as defined in DbEntries.py. Models take the form of Qt item models,
# for display/editing purposes. Note that the models do not automatically react to 
# any changes originating reloading the database entries, the controller must call the respective functions.
# Note that all these models are NOT editable, they only change by outside command.

from . import DbEntries
from . import BrowserState
from . import Utilities

from PyQt5 import QtCore, QtGui, QtWidgets

SacredItemRole = QtCore.Qt.UserRole + 1

# experiment colors
# # # DuplicateColor = QtGui.QColor(255,255,150)
FailedColor = QtGui.QColor(255,50,50)
InterruptedColor = QtGui.QColor(255,150,150)
RunningColor = QtGui.QColor(200,200,255)

class StudyTreeModel(QtCore.QAbstractItemModel):

    ################## Initialize ##################
    def __init__(self,connection):
        super().__init__()
        self._connection = connection 
        # a sacred connection, i.e. the root of database access. Currently not replaceable?

        # make connections at all levels. Don't forget to reconnect the studies whenever anything changes
        self._connection.databases_to_be_changed.connect(self._slot_databases_to_be_changed)
        self._connection.databases_changed.connect(self._slot_databases_changed)

    def index(self,row,column,parent):
        if not parent.isValid():
            # this is an index for a database
            dbname = self._connection.list_databases()[row]
            dbitem = self._connection.get_database(dbname)
            return self.createIndex(row,column,dbitem)
        else:
            # this refers to a study; take the parent database from the parent index
            database = parent.internalPointer()
            studyname = database.list_studies()[row]
            studyitem = database.get_study(studyname)
            return self.createIndex(row,column,studyitem)

    def parent(self,index):
        assert index.isValid()
        item = index.internalPointer()
        assert item.typename() in [ 'SacredDatabase', 'SacredStudy' ]
        if item.typename() == 'SacredDatabase':
            return QtCore.QModelIndex()
        else:
            parent_database = item.get_database()
            parent_name = parent_database.id()
            connection = parent_database.get_connection()
            parent_row = connection.list_databases().index(parent_name)
            return self.createIndex(parent_row,0,parent_database)

    def rowCount(self,parent):
        if not parent.isValid():
            item = self._connection
        else:
            item = parent.internalPointer()

        if not item.is_initialized():
#             print('For item %s, rowCount is not initialized, return 0' % item.name())
            return 0
        else:
            if item.typename() == 'SacredConnection':
#                 print('Returning %d rows for connection' % len(item.list_databases()))
#                 print('For item %s of type connection, rowCount is %d' % (item.name(),len(item.list_databases())))
                return len(item.list_databases())
            elif item.typename() == 'SacredDatabase':
#                 print('Returning %d rows for database %s' % (len(item.list_studies()),item.id()))
#                 print('For item %s of type database, rowCount is %d' % (item.name(),len(item.list_studies())))
                return len(item.list_studies())
            elif item.typename() == 'SacredStudy':
#                 print('Returning 0 rows for study',item.name())
                return 0
            else:
                raise Exception('Unexpected sacred item type!')

    def columnCount(self,parent):
        return 1

    def data(self,index,role):
        if not index.isValid():
            return None
        item = index.internalPointer()
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.ToolTipRole:
            return item.id()
        elif role == SacredItemRole:
            return item
        else:
            return None

    def headerData(self,section,orientation,role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            if section == 0:
                return 'Database Element'
        return None

    def sacred_from_index(self,index):
        return index.internalPointer()

    def index_from_sacred(self,sacred_item):
        if sacred_item.typename() == 'SacredDatabase':
            parent_connection = sacred_item.get_connection()
            row = parent_connection.list_databases().index(sacred_item.id())
            return self.createIndex(row,0,sacred_item)
        elif sacred_item.typename() == 'SacredStudy':
            parent_database = sacred_item.get_database()
            row = parent_database.list_studies().index(sacred_item.id())
            return self.createIndex(row,0,sacred_item)
        else:
            raise Exception('Wrong type')

    def _connect_database_slots(self,db): 
        # connection will be deleted automatically when the database is deleted
        db.studies_to_be_changed.connect(self.slot_studies_to_be_changed)
        db.studies_changed.connect(self.slot_studies_changed)

    def _slot_databases_to_be_changed(self,connection,change_data):
        parent = QtCore.QModelIndex()
        if change_data[0] == DbEntries.ChangeType.Reset:
            self.beginResetModel()
        elif change_data[0] == DbEntries.ChangeType.Content:
            pass
        elif change_data[0] == DbEntries.ChangeType.Insert:
            first = change_data.info[0]
            last = change_data.info[0] + change_data.info[1] - 1
            self.beginInsertRows(parent,first,last)
        elif change_data[0] == DbEntries.ChangeType.Remove:
            first = change_data.info[0]
            last = change_data.info[0] + change_data.info[1] - 1
            self.beginRemoveRows(parent,first,last)

    def _slot_databases_changed(self,connection,change_data):
        parent = QtCore.QModelIndex()
        if change_data[0] == DbEntries.ChangeType.Reset:
            self.endResetModel()
            # connect slots for all databases
            for n in self._connection.list_databases():
                db = self._connection.get_database(n)
                self._connect_database_slots(db)
        elif change_data[0] == DbEntries.ChangeType.Content:
            for row in change_data.info:
                idx = self.index(row,0,parent)
                self.dataChanged.emit(idx,idx)
        elif change_data[0] == DbEntries.ChangeType.Insert:
            self.endInsertRows()
            # connect slot for this database
            n = self._connection.list_databases()[change_data[1][0]]
            db = self._connection.get_database(n)
            self._connect_database_slots(db)
        elif change_data[0] == DbEntries.ChangeType.Remove:
            self.endRemoveRows()

    def slot_studies_to_be_changed(self,database,change_data):
        print('Received signal studies_to_be_changed')
        parent = self.index_from_sacred(database)
        if change_data[0] == DbEntries.ChangeType.Reset:
            self.beginResetModel()
        elif change_data[0] == DbEntries.ChangeType.Content:
            pass
        elif change_data[0] == DbEntries.ChangeType.Insert:
            first = change_data.info[0]
            last = change_data.info[0] + change_data.info[1] - 1
            self.beginInsertRows(parent,first,last)
#             print('Studies changed: inserting rows to',parent.internalPointer().name(),first,last)
        elif change_data[0] == DbEntries.ChangeType.Remove:
            first = change_data.info[0]
            last = change_data.info[0] + change_data.info[1] - 1
            self.beginRemoveRows(parent,first,last)

    def slot_studies_changed(self,database,change_data):
        print('Received signal studies_changed')
        parent = self.index_from_sacred(database)
        if change_data[0] == DbEntries.ChangeType.Reset:
            self.endResetModel()
        elif change_data[0] == DbEntries.ChangeType.Content:
            for row in change_data.info:
                idx = self.index(row,0,parent)
                self.dataChanged.emit(idx,idx)
        elif change_data[0] == DbEntries.ChangeType.Insert:
            self.endInsertRows()
#             print('Studies changed: insertED rows to',parent.internalPointer().name(),' and now rowCount is',self.rowCount(parent))
            self.dataChanged.emit(parent,parent)
        elif change_data[0] == DbEntries.ChangeType.Remove:
            self.endRemoveRows()


# note that via the SacredItemRole, whole experiments are returned (ignoring the column id)
class ExperimentListModel(QtCore.QAbstractTableModel):
    def __init__(self,browser_state):
        super().__init__()
        self._browser_state = browser_state # note that this is immutable, however contains pointers to mutable elements
        self._sort_cache = None

        self._browser_state.current_study.study_about_to_be_changed.connect(self.slot_study_to_be_changed)
        self._browser_state.current_study.study_changed.connect(self.slot_study_changed)
        self._browser_state.sort_order.sort_order_to_be_changed.connect(self.slot_sort_order_to_be_changed)
        self._browser_state.sort_order.sort_order_changed.connect(self.slot_sort_order_changed)
        self._browser_state.fields.visible_fields_to_be_changed.connect(self.slot_visible_fields_to_be_changed)
        self._browser_state.fields.visible_fields_changed.connect(self.slot_visible_fields_changed)
        self._browser_state.general_settings.view_mode_to_be_changed.connect(self.slot_view_mode_to_be_changed)
        self._browser_state.general_settings.view_mode_changed.connect(self.slot_view_mode_changed)
        self._browser_state.general_settings.column_widths_to_be_changed.connect(self.slot_column_widths_to_be_changed)
        self._browser_state.general_settings.column_widths_changed.connect(self.slot_column_widths_changed)

        # note that in the respective slot functions, further connections are made

    def rowCount(self,idx):
        study = self._browser_state.current_study.get_study()
        return len(study.list_experiments()) if study is not None else 0

    def columnCount(self,idx):
        return self._browser_state.fields.visible_fields_count()

    def data(self,index,role):
        if self._sort_cache is None:
            return None # not initialized, no study set

        row = index.row()
        col = index.column()

        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.ToolTipRole:
            # translate row into experiment
            exp_id = self._sort_cache.get_sorted_experiment_ids()[row]
            exp = self._browser_state.current_study.get_study().get_experiment(exp_id)


            # translate column into field
            fieldname = self._browser_state.fields.get_visible_fields()[col]
            value = exp.get_field(fieldname)
            # if value is a result, process it according to view mode
            if fieldname[0]== BrowserState.Fields.FieldType.Result:
                processed_value = Utilities.process_result(value,self._browser_state.general_settings.get_view_mode())
            else:
                processed_value = value

            return processed_value
        elif role == QtCore.Qt.BackgroundColorRole:
            # translate row into experiment
            exp_id = self._sort_cache.get_sorted_experiment_ids()[row]
            exp = self._browser_state.current_study.get_study().get_experiment(exp_id)
            status = exp.get_status()
            if status == 'FAILED':
                return QtGui.QBrush(FailedColor)
            elif status == 'INTERRUPTED':
                return QtGui.QBrush(InterruptedColor)
            elif status == 'RUNNING':
                return QtGui.QBrush(RunningColor)
            else:
                return None

        elif role == SacredItemRole:
            exp_id = self._sort_cache.get_sorted_experiment_ids()[row]
            exp = self._browser_state.current_study.get_study().get_experiment(exp_id)
            return exp

        else:
            return None

    def headerData(self,index,orientation,role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Vertical:
                return '%d' % index
            else:
                return self._browser_state.fields.get_visible_fields()[index][1]
        else:
            return super().headerData(index,orientation,role)

    ############# Slots for changed data #############
    def slot_study_to_be_changed(self,study):
        # remove existing connections
        old_study = self._browser_state.current_study.get_study()
        if old_study is not None:
            # must exist
            old_study.experiments_to_be_reset.disconnect(self.slot_experiments_to_be_reset_closure)
            old_study.experiments_reset.disconnect(self.slot_experiments_reset_closure)

        self.beginResetModel()

    def slot_study_changed(self,study):
        if self._sort_cache is None:
            # so we avoid initializing the sort cache before data is actually ready
            self._sort_cache = Utilities.SortCache()

        if study is not None:
            self._sort_cache.set_experiments(list(self._browser_state.current_study.get_study().get_all_experiments().values()))

        self.endResetModel()

        # make connections, note that the connections from the previous study are already removed
        self.slot_experiments_to_be_reset_closure = self.slot_experiments_to_be_reset
        study.experiments_to_be_reset.connect(self.slot_experiments_to_be_reset_closure)
        self.slot_experiments_reset_closure = self.slot_experiments_reset
        study.experiments_reset.connect(self.slot_experiments_reset_closure)
    
    def slot_experiments_to_be_reset(self):
        if self._sort_cache is None:
            # so we avoid initializing the sort cache before data is actually ready
            self._sort_cache = Utilities.SortCache()
        self.beginResetModel() # make it all new

    def slot_experiments_reset(self):
        self._sort_cache.set_experiments(list(self._browser_state.current_study.get_study().get_all_experiments().values()))
        self.endResetModel()

    def slot_visible_fields_to_be_changed(self,change_data):
        self.beginResetModel()  # TODO update only columns!!!!!

    def slot_visible_fields_changed(self,visible,change_data):
        if self._sort_cache is None:
            # so we avoid initializing the sort cache before data is actually ready
            self._sort_cache = Utilities.SortCache()
        self.endResetModel()

    def slot_sort_order_to_be_changed(self):
        if self._sort_cache is None:
            # so we avoid initializing the sort cache before data is actually ready
            self._sort_cache = Utilities.SortCache()
        self.beginResetModel() # make it all new

    def slot_sort_order_changed(self,order_was_reset):
        if self._sort_cache is None:
            # so we avoid initializing the sort cache before data is actually ready
            self._sort_cache = Utilities.SortCache()

        self._sort_cache.set_sort_order(self._browser_state.sort_order.get_order())
        self.endResetModel()

    def slot_column_widths_to_be_changed(self,field,width):
        pass

    def slot_column_widths_changed(self,field,width):
        pass

    def slot_view_mode_to_be_changed(self,new_mode):
        pass # boh...

    def slot_view_mode_changed(self,new_mode):
        parent = QtCore.QModelIndex()
        # TODO: find out which columns are result columns, emit change signal
        void_idx = QtCore.QModelIndex()
        from_idx = self.index(0,0,parent)
        to_idx = self.index(self.rowCount(void_idx) - 1,self.columnCount(void_idx) - 1,parent)
        self.dataChanged.emit(from_idx,to_idx)


