# This file contains objects which represent QT models to encapsulate browser state
# (see BrowserState.py) which is NOT contained in any database (for that, see DbEntries.py and
# DbModel.py). Note that the models do not automatically react to 
# any changes originating reloading the database entries, the controller must call the respective functions.
# Note that all these models are NOT editable, they only change by outside command.

from PyQt5 import QtCore, QtGui, QtWidgets

from . import BrowserState

class InvisibleFieldsModel(QtCore.QAbstractListModel):
    def __init__(self,fields):
        super().__init__()
        self._fields = fields # an instance of BrowserState.Fields

    def rowCount(self,idx):
        assert not idx.isValid() # we only have top level data
        return self._fields.invisible_fields_count()

    def data(self,index,role):
        row = index.row() # only relevant thing
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.ToolTipRole:
            return self._fields.get_invisible_fields()[row][1] # remove the type
        else:
            return None

    def slot_invisible_fields_to_be_changed(self,change_data):
        # for the interpretation of change_data see BrowserState.py
        if change_data.tp == BrowserState.Fields.ChangeType.Reset:
            self.beginResetModel()
        elif change_data.tp == BrowserState.Fields.ChangeType.Content:
            pass
        elif change_data.tp == BrowserState.Fields.ChangeType.Insert:
            first = change_data.info[0]
            last = change_data.info[0] + change_data.info[1] - 1
            self.beginInsertRows(QtCore.QModelIndex(),first,last)
        elif change_data.tp == BrowserState.Fields.ChangeType.Remove:
            first = change_data.info[0]
            last = change_data.info[0] + change_data.info[1] - 1
            self.beginRemoveRows(QtCore.QModelIndex(),first,last)

    def slot_invisible_fields_changed(self,new_fields,change_data):
        # for the interpretation of change_data see BrowserState.py
        if change_data.tp == BrowserState.Fields.ChangeType.Reset:
            self.endResetModel()
        elif change_data.tp == BrowserState.Fields.ChangeType.Content:
            for row in change_data.info:
                idx = self.index(row,0,QtCore.QModelIndex())
                self.dataChanged.emit(idx,idx)
        elif change_data.tp == BrowserState.Fields.ChangeType.Insert:
            self.endInsertRows()
        elif change_data.tp == BrowserState.Fields.ChangeType.Remove:
            self.endRemoveRows()

class VisibleFieldsModel(QtCore.QAbstractListModel):
    def __init__(self,fields):
        super().__init__()
        self._fields = fields # an instance of BrowserState.Fields

    def rowCount(self,idx):
        assert not idx.isValid() # we only have top level data
        return self._fields.visible_fields_count()

    def data(self,index,role):
        row = index.row() # only relevant thing
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.ToolTipRole:
            return self._fields.get_visible_fields()[row][1]
        else:
            return None

    def slot_visible_fields_to_be_changed(self,change_data):
        # for the interpretation of change_data see BrowserState.py
        if change_data.tp == BrowserState.Fields.ChangeType.Reset:
            self.beginResetModel()
        elif change_data.tp == BrowserState.Fields.ChangeType.Content:
            pass
        elif change_data.tp == BrowserState.Fields.ChangeType.Insert:
            first = change_data.info[0]
            last = change_data.info[0] + change_data.info[1] - 1
            self.beginInsertRows(QtCore.QModelIndex(),first,last)
        elif change_data.tp == BrowserState.Fields.ChangeType.Remove:
            first = change_data.info[0]
            last = change_data.info[0] + change_data.info[1] - 1
            self.beginRemoveRows(QtCore.QModelIndex(),first,last)

    def slot_visible_fields_changed(self,new_fields,change_data):
        print('SMACKY slot_visible_fields_changed CALLED')
        # for the interpretation of change_data see BrowserState.py
        if change_data.tp == BrowserState.Fields.ChangeType.Reset:
            self.endResetModel()
        elif change_data.tp == BrowserState.Fields.ChangeType.Content:
            for row in change_data.info:
                idx = self.index(row,0,QtCore.QModelIndex())
                self.dataChanged.emit(idx,idx)
        elif change_data.tp == BrowserState.Fields.ChangeType.Insert:
            self.endInsertRows()
        elif change_data.tp == BrowserState.Fields.ChangeType.Remove:
            self.endRemoveRows()




