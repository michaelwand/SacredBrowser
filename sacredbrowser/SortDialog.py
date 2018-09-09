if __name__ == '__main__':
    import BrowserState
else:
    from . import BrowserState

from PyQt5 import QtCore, QtWidgets, QtWidgets

# The Sort dialog, with a grid of sorting buttons
class SortDialog(QtWidgets.QDialog):
    # Constant giving the number of search keys
    MaxSortKeyCount = 6

    ############# Signals #############
        
    sort_request = QtCore.pyqtSignal(tuple,int) # tuple would be a field of form (type,text)
    dialog_closed = QtCore.pyqtSignal()

    ############# Main Part #############
        
    def __init__(self,sort_order):
        super().__init__()
        
        self._sort_order = sort_order

        self._sort_order.sort_order_changed.connect(self._slot_sort_order_changed)

        self._init_layout()

        self._update_layout()

        self.show()

    def _init_layout(self):

        # list of lists (row,col), where each row must have MaxSortKeyCount elements
        # (which can be visible or hidden)
        self._sort_buttons = []

        # single list (of QLabels)
        self._sort_labels = []

        # initialize an empty grid layout for the sort buttons and labels
        self._sort_layout = QtWidgets.QGridLayout()
        self._close_button = QtWidgets.QPushButton('Close')
        self._main_layout = QtWidgets.QVBoxLayout()
        self._main_layout.addLayout(self._sort_layout)
        self._main_layout.addWidget(self._close_button)
        self.setLayout(self._main_layout)

        # connect
        self._close_button.clicked.connect(self.close)

    def _update_layout(self):
        # TODO maybe divide this in two functions, depending on whether the list of available field
        # has changed?

        # make enough rows to cover all fields
        if len(self._sort_order.get_available_fields()) > len(self._sort_buttons):
            for i in range(len(self._sort_order.get_available_fields()) - len(self._sort_buttons)):
                self._add_button_row()

        # make the right number of rows visible
        self._make_visible(len(self._sort_order.get_available_fields()),len(self._sort_order.get_available_fields()))

        # update labels and status
        self._update_labels()
        self._update_button_state()


    # adds a single row of buttons
    def _add_button_row(self):
        new_row_number = len(self._sort_buttons)
        new_label = QtWidgets.QLabel('Row %d' % new_row_number)
        new_buttons = [ QtWidgets.QPushButton(str(i+1)) for i in range(self.MaxSortKeyCount) ]
        self._sort_labels.append(new_label)
        self._sort_buttons.append(new_buttons)
        self._sort_layout.addWidget(new_label,new_row_number,0)

        def bind_slot(row,col):
            res = lambda: self._slot_sort_button_clicked(row,col)
            return res

        for pos,bt in enumerate(new_buttons):
            bt.setCheckable(True)
            self._sort_layout.addWidget(bt,new_row_number,pos+1)
            # make closure
#             print('Lambda bound:',new_row_number,pos)
#             def slot_func(pos2=pos):
#                 print('slot_func: pos2 is %d (id %s)' % (pos2,id(pos2)))
#                 self._slot_sort_button_clicked(new_row_number,pos2)
#             bt.clicked.connect(slot_func)
            bt.clicked.connect(bind_slot(new_row_number,pos))

    # makes the upper left number of buttons visible, hides the rest
    def _make_visible(self,vis_row_count,vis_col_count):
        for row in range(len(self._sort_labels)):
#             self._sort_labels[row].setEnabled(row < vis_row_count)
            if row < vis_row_count:
                self._sort_labels[row].show()
            else:
                self._sort_labels[row].hide()

            for col in range(self.MaxSortKeyCount):
                if row < vis_row_count and col < vis_col_count:
                    self._sort_buttons[row][col].show()
                else:
                    self._sort_buttons[row][col].hide()
#                 self._sort_buttons[row][col].setEnabled(row < vis_row_count and col < vis_col_count)
                # TODO

    def _update_labels(self):
        for pos,field in enumerate(self._sort_order.get_available_fields()):
            field_type,field_text = field
            if field_type == BrowserState.Fields.FieldType.Result:
                formatted_field_text = '<i>' + field_text + '</i>'
            else:
                formatted_field_text = field_text
            self._sort_labels[pos].setText(formatted_field_text)

    def _update_button_state(self):
        order = self._sort_order.get_order()
        # order is a list of fields

        for row,field in enumerate(self._sort_order.get_available_fields()):
            try:
                sel_col = order.index(field)
            except ValueError:
                sel_col = -1

            for col in range(self.MaxSortKeyCount):
                self._sort_buttons[row][col].setChecked(col == sel_col)



    ############# Slots and events #############
    
    def _slot_sort_order_to_be_changed(self):
        pass

    def _slot_sort_order_changed(self,new_order):
        self._update_layout()


    def _slot_sort_button_clicked(self,row,col):
        field = self._sort_order.get_available_fields()[row]
        print('SORT BUTTON CLICKED: %d / %d, field is %s' % (row,col,field))
        self.sort_request.emit(field,col)

    def closeEvent(self,e):
        print('Close event!')
        self.dialog_closed.emit()
        super().closeEvent(e)

if __name__ == '__main__':
    class TestApp(QtWidgets.QApplication):
        def __init__(self):
            super().__init__([])

            # make sort order object
            self._sort_order = BrowserState.SortOrder()
            # major functions: set_available_fields, sort_request
    
            # placeholder for sort dialog if present
            self._sort_dialog = None

            # make window
            self._main_win = QtWidgets.QWidget()
            self._field_edit = QtWidgets.QTextEdit()
            self._dialog_button = QtWidgets.QPushButton('Dialog')
            self._dialog_button.setCheckable(True)
            self._set_fields_button = QtWidgets.QPushButton('Set Fields')
            self._close_button = QtWidgets.QPushButton('Close')

            self._layout = QtWidgets.QVBoxLayout()
            self._layout.addWidget(self._field_edit)
            self._layout.addWidget(self._dialog_button)
            self._layout.addWidget(self._set_fields_button)
            self._layout.addWidget(self._close_button)
            self._main_win.setLayout(self._layout)
            self._main_win.show()

            # connections
            self._close_button.clicked.connect(self.quit,QtCore.Qt.QueuedConnection)
            self._dialog_button.clicked.connect(self._slot_dialog_button_clicked)
            self._set_fields_button.clicked.connect(self._slot_set_fields_button_clicked)

        def _slot_dialog_button_clicked(self):
            if self._sort_dialog is None:
                self._sort_dialog = SortDialog(self._sort_order)
                self._sort_dialog.dialog_closed.connect(self._slot_dialog_closed)
                self._sort_dialog.sort_request.connect(self._sort_order.sort_request)
                self._sort_dialog.show()

                self._dialog_button.setChecked(True)
            else:
                self._sort_dialog.deleteLater()
                self._sort_dialog = None
                self._dialog_button.setChecked(False)

        def _slot_set_fields_button_clicked(self):
#             if self._sort_dialog is not None:
            field_texts = self._field_edit.toPlainText().split('\n')
            fields = [ (1,f) for f in field_texts ]
            self._sort_order.set_available_fields(fields)

        def _slot_dialog_closed(self):
            self._sort_dialog.deleteLater()
            self._sort_dialog = None

            self._dialog_button.setChecked(False)

if __name__ == '__main__':
    app = TestApp()
    QtCore.pyqtRemoveInputHook()
    app.exec_()

