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

    def __init__(self,browser_state):
        super(ExperimentListView,self).__init__()
        self._browser_state = browser_state

        self._browser_state.general_settings.column_width_to_be_changed.connect(self.slot_column_width_to_be_changed)
        self._browser_state.general_settings.column_width_changed.connect(self.slot_column_width_changed)

        self._browser_state.fields.visible_fields_changed.connect(self.slot_visible_fields_changed)

        self._browser_state.current_study.study_to_be_changed.connect(self.slot_study_to_be_changed)

        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding)

        vh = self.verticalHeader()
        vh.setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        vh.setDefaultSectionSize(self.RowHeight)

        self.horizontalHeader().sectionResized.connect(self.slot_column_resized)

        # flag which indicates that study is loading, in this case will defer column resize signals until
        # visible fields have been loaded
        self._waiting_for_field_change = False
#         self._deferred_column_width_changes = []

    ############## QT overloads ##############

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
        print('QUAAAAAAAAAAAAAk')
        self.column_resized.emit(column,new_width)

    ############## SacredBrowser functions ##############

    # Reset all columns to the width saved in browser state
    def reset_column_widths(self):
        fields = self._browser_state.fields.get_visible_fields()
        for col,fld in enumerate(fields):
            this_col_width = self._browser_state.general_settings.get_column_width(fld)
            self.setColumnWidth(col,this_col_width)

    # Called from the browser state if the column width is changed programmatically
    def slot_column_width_to_be_changed(self,field,new_width):
        pass

    # Called from the browser state if the column width is changed programmatically
    def slot_column_width_changed(self,field,new_width):
        if not self._waiting_for_field_change:
            print('********** ExpListView: slot_column_width_changed(%s,%s) cqalled, visible fields are %s' % (field,new_width, self._browser_state.fields.get_visible_fields()))
            # determine which column number that actually is
            current_fields = self._browser_state.fields.get_visible_fields()
            try:
                col = current_fields.index(field)
                self.setColumnWidth(col,new_width)
            except ValueError:
                pass # field not present

    # Called when the list of visible fields has changed. Adapt the column widths.
    def slot_visible_fields_changed(self,fields,dummy):
        print('********** ExpListView: slot_visible_fields_changed')
        self._waiting_for_field_change = False
        self.reset_column_widths()

    # Called when the study is to be changed. This causes the view to DEFER all requests to change the column
    # width until the signal that the visible fields have been loaded has arrived (avoid sync issues).
    def slot_study_to_be_changed(self):
        print('********** ExpListView: study to be changed')
        self._waiting_for_field_change = True

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
