from __future__ import division
from __future__ import print_function

from PyQt5 import QtCore, QtGui, QtWidgets

class ExperimentListView(QtWidgets.QTableView):
    
    ########################################################
    ## CONSTANT
    ########################################################

    # Height of rows (note that column widths are more variable and 
    # handled by the model)
    RowHeight = 18

    ########################################################
    ## SIGNALS
    ########################################################
    full_entry_requested = QtCore.pyqtSignal() 
    copy_requested = QtCore.pyqtSignal() 
    delete_requested = QtCore.pyqtSignal()

    column_resized = QtCore.pyqtSignal(int,int) # column index and new size

    ########################################################
    ## INITIALIZATION
    ########################################################

    def __init__(self):
        super(ExperimentListView,self).__init__()

        self.setSizePolicy (QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding)

        vh = self.verticalHeader()
        vh.setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        vh.setDefaultSectionSize(self.RowHeight)

        self.horizontalHeader().sectionResized.connect(self.slot_column_resized)

    ########################################################
    ## SLOTS AND OVERLOADS
    ########################################################

    # QT overload for key events
    def keyPressEvent(self,event):
        if event.matches(QtGui.QKeySequence.Copy):
            self.copy_requested.emit()
            event.accept()
            return
        elif event.key() == QtCore.Qt.Key_Delete:
            self.delete_requested.emit()
            event.accept()
            return
        elif event.key() == QtCore.Qt.Key_Enter:
            self.full_entry_requested.emit()
            event.accept()
            return
        else:
            event.ignore()
            super().keyPressEvent(event)
            return

    # QT overload for mouse double click (calls details dialog)
    def mouseDoubleClickEvent(self, event):
        self.full_entry_requested.emit()

    # Called from the runtime when the column size changes. 
    def slot_column_resized(self,column,old_width,new_width):
        self.column_resized.emit(column,new_width)

#     ########################################################
#     ## HELPERS
#     ########################################################
# 
#     # retrieve column widths from the widget
#     def _getColumnWidths(self):
#         return [ self.columnWidths(i) for i in range(self.model().columnCount()) ]
# #         columnWidths = {}
# #         for i in range(self.model().columnCount()):
# #             thisField = self.model().headerData(i,QtCore.Qt.Horizontal,QtCore.Qt.DisplayRole)
# #             columnWidths[thisField] = self.columnWidth(i) 
# #         return columnWidths
# 
#     # sets the column widths, to be called internally
#     def _setColumnWidths(self,new_widths):
#         # note that the new widths must fit the model
#         assert len(new_widths) == self.model().columnCount()
#         for i in range(self.model().columnCount()):
#             self.setColumnWidth(i,new_widths[i])
# #         print('Call to SCW:',cwDict)
# #         if len(cwDict) == 0:
# #             pass
# #         for i in range(self.model().columnCount()):
# #             thisField = self.model().headerData(i,QtCore.Qt.Horizontal,QtCore.Qt.DisplayRole)
# # #             thisWidth = cwDict.get(thisField,self.DefaultColumnWidth)
# #             thisWidth = cwDict[thisField]
# #             self.setColumnWidth(i,thisWidth)
# 
