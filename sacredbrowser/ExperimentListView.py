from __future__ import division
from __future__ import print_function

from PyQt4 import QtCore, QtGui

class ExperimentListView(QtGui.QTableView):
    
    ########################################################
    ## CONSTANT
    ########################################################

    # Height of rows (note that colulmn widths are more variable and 
    # handled by the model)
    RowHeight = 18

    ########################################################
    ## INITIALIZATION
    ########################################################

    def __init__(self):
        super(ExperimentListView,self).__init__()

        self.setSizePolicy (QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Expanding)

        self.controller = None # TODO rename

        vh = self.verticalHeader()
        vh.setResizeMode(QtGui.QHeaderView.Fixed)
        vh.setDefaultSectionSize(self.RowHeight)

        self.horizontalHeader().sectionResized.connect(self.slotSectionResized)

    ########################################################
    ## SLOTS AND OVERLOADS
    ########################################################

    # QT overload for key events
    def keyPressEvent(self,event):
        if event.matches(QtGui.QKeySequence.Copy):
            self.controller.slotCopyToClipboard()
            event.accept()
            return
        elif event.key() == QtCore.Qt.Key_Delete:
            self.controller.slotDeleteSelection()
            event.accept()
            return
        elif event.key() == QtCore.Qt.Key_Enter:
            self.controller.slotFullEntry()
            event.accept()
            return
        else:
            event.ignore()
            super(ExperimentListView,self).keyPressEvent(event)
            return

    # QT overload for mouse double click (calls details dialog)
    def mouseDoubleClickEvent(self, event):
        self.controller.slotFullEntry()

    # Called from the runtime when the column size changes. 
    def slotSectionResized(self,column,oldWidth,newWidth):
        self.controller.columnWidthsChangedFromGui(self._getColumnWidths())

    # Called from the runtime when the selection has changed
    def selectionChanged(self,selected,deselected):
        super(ExperimentListView,self).selectionChanged(selected,deselected)
        # also inform the controller
        self.controller.selectionChanged()

    # Called from the framework when the displayed data has changed. This might mean that
    # the data order has changed, or a new subset of data is displayed, or even
    # a new collection is displayed. Completely reread configuration.
    def dataChanged(self,topLeft,bottomRight):
#         cwDict = self.loadColumnWidths()
#         if cwDict is not None:
#             self.setColumnWidths(cwDict)
# 
        
        columnWidths = self.controller.getColumnWidths()
        self._setColumnWidths(columnWidths)
        super(ExperimentListView,self).dataChanged(topLeft,bottomRight)

    ########################################################
    ## HELPERS
    ########################################################

    # retrieve column widths from the widget
    def _getColumnWidths(self):
        columnWidths = {}
        for i in range(self.model().columnCount()):
            thisField = self.model().headerData(i,QtCore.Qt.Horizontal,QtCore.Qt.DisplayRole)
            columnWidths[thisField] = self.columnWidth(i) 
        return columnWidths

    # sets the column widths, to be called internally
    def _setColumnWidths(self,cwDict):
        print('Call to SCW:',cwDict)
        if len(cwDict) == 0:
            pass
        for i in range(self.model().columnCount()):
            thisField = self.model().headerData(i,QtCore.Qt.Horizontal,QtCore.Qt.DisplayRole)
#             thisWidth = cwDict.get(thisField,self.DefaultColumnWidth)
            thisWidth = cwDict[thisField]
            self.setColumnWidth(i,thisWidth)

