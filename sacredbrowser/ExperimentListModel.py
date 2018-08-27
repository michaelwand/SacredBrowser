raise Exception('OUTDATED')
from PyQt5 import QtCore, QtGui

import time
import re

import pymongo
import bson

from . import Config
from . import DetailsDialog

class ExperimentListModel(QtCore.QAbstractTableModel):
    ########################################################
    ## CONSTANTS
    ########################################################

    # color backgrounds for database entries with different properties
    # according to the Qt model, these are actually MODEL properties, not VIEW properties
    DuplicateColor = QtGui.QColor(255,255,150)
    FailedColor = QtGui.QColor(255,50,50)
    InterruptedColor = QtGui.QColor(255,150,150)
    RunningColor = QtGui.QColor(200,200,255)

    ########################################################
    ## INITIALIZATION
    ########################################################

    # constructor
    def __init__(self,application):
        
        self.application = application
        self.controller = None

        # might have to go last
        super(ExperimentListModel,self).__init__()

    def getApplication(self):
        return self.application

    ########################################################
    ## OVERLOADS
    ########################################################
    def rowCount(self, parent = None):
        return len(self.controller.getCollectionData())

    def columnCount(self, parent = None):
        return len(self.controller.getDisplayedFields())

    # Main accessor function to the data underlying this model
    def data(self, index, role):
        if not index.isValid():
            return None
        entry = self.controller.getCollectionData()[index.row()][1]
        field = self.controller.getDisplayedFields()[index.column()]
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.ToolTipRole:
            if re.match(r'^Result [0-9]+$',field):
                # return a formatted result
                try:
                    number = int(re.match(r'^Result ([0-9]+)$',field).groups()[0]) - 1 # counting!!!
                    resValue = float(entry['result'][number])
                    res = self.controller.formatResultValue(resValue)
                except (KeyError,IndexError,TypeError):
                    res = '---'
            else:
                # return a configuration value
                try:
                    res = entry['config'][field]
                except KeyError:
                    res = 'XXX'
            return str(res)
        elif role == QtCore.Qt.BackgroundColorRole:
            if entry['DuplicateMarker']:
                return QtGui.QBrush(self.DuplicateColor)
            elif entry['status'] == 'FAILED':
                return QtGui.QBrush(self.FailedColor)
            elif entry['status'] == 'INTERRUPTED':
                return QtGui.QBrush(self.InterruptedColor)
            elif entry['status'] == 'RUNNING':
                return QtGui.QBrush(self.RunningColor)
            else:
                return None
        else:
            return None

    # column (field) headers
    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return self.controller.getDisplayedFields()[section]
            elif orientation == QtCore.Qt.Vertical:
                return str(section)
        else:
            return None

    ########################################################
    ## MAIN PART
    ########################################################

    # Called when the underlying data is about to change.
    def dataAboutToBeChanged(self):
        self.layoutAboutToBeChanged.emit()

    # Called when the underlying data has been changed.
    def dataHasBeenChanged(self):
        self.layoutChanged.emit()
        upperLeftIndex = self.index(0,0)
        lowerRightIndex = self.index(len(self.controller.getCollectionData()), len(self.controller.getDisplayedFields()))
        self.dataChanged.emit(upperLeftIndex,lowerRightIndex)

