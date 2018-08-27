from PyQt5 import QtCore, QtGui, QtWidgets

import sys


# This class implements a widget consisting of two lists. The first one contains a selection of 
# available items, the right one a (sorted) list of chosen items. Items may be moved between the lists,
# as well as sorted within the list of chosen items.
# The widget manages the selection model for the list views adn enables/disables buttons accordingly.
# The actual logic is in the controller and BrowserState modules. 
class FieldChoiceWidget(QtWidgets.QWidget):

    ############# Signals #############

    add_button_clicked = QtCore.pyqtSignal()
    remove_button_clicked = QtCore.pyqtSignal()
    up_button_clicked = QtCore.pyqtSignal()
    down_button_clicked = QtCore.pyqtSignal()

    ############# Public interface #############
    def __init__(self):
        super().__init__()
        self.setSizePolicy (QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding)

        # FIXME TODO debug only
#         p = self.palette()
#         p.setColor(self.backgroundRole(), QtCore.Qt.red)
#         self.setPalette(p)
#         self.setAutoFillBackground(True)

        # make subwidgets
        self._invisible_fields_display = QtWidgets.QListView()
        self._invisible_fields_display.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._invisible_fields_display.setSizePolicy(QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding)
        self._invisible_fields_selection_model = self._invisible_fields_display.selectionModel()
        assert self._invisible_fields_selection_model is None

        self._visible_fields_display = QtWidgets.QListView()
        self._visible_fields_display.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._visible_fields_display.setSizePolicy(QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding)
        self._visible_fields_selection_model = self._visible_fields_display.selectionModel()
        assert self._visible_fields_selection_model is None
      
        self._add_button = QtWidgets.QPushButton('+')
        self._add_button.setSizePolicy(QtWidgets.QSizePolicy.Preferred,QtWidgets.QSizePolicy.Expanding)
        self._remove_button = QtWidgets.QPushButton('-')
        self._remove_button.setSizePolicy(QtWidgets.QSizePolicy.Preferred,QtWidgets.QSizePolicy.Expanding)
        self._up_button = QtWidgets.QPushButton('UP')
        self._up_button.setSizePolicy(QtWidgets.QSizePolicy.Preferred,QtWidgets.QSizePolicy.Expanding)
        self._down_button = QtWidgets.QPushButton('DOWN')
        self._down_button.setSizePolicy(QtWidgets.QSizePolicy.Preferred,QtWidgets.QSizePolicy.Expanding)

        self._update_button_status()

        # connect
        self._add_button.clicked.connect(self._slot_add_button_clicked)
        self._remove_button.clicked.connect(self._slot_remove_button_clicked)
        self._up_button.clicked.connect(self._slot_up_button_clicked)
        self._down_button.clicked.connect(self._slot_down_button_clicked)
        # note that connections regarding the selection model are made when models are set (i.e. in set_models)

        # make layout
        self._layout = QtWidgets.QGridLayout()
        self._layout.addWidget(self._invisible_fields_display,0,0,2,1)
        self._layout.addWidget(self._add_button,0,1,1,1)
        self._layout.addWidget(self._remove_button,1,1,1,1)
      
        self._layout.addWidget(self._visible_fields_display,0,2,2,1)
        self._layout.addWidget(self._up_button,0,3,1,1)
        self._layout.addWidget(self._down_button,1,3,1,1)

        self.setLayout(self._layout)

    def set_models(self,invisible_fields_model,visible_fields_model):
        self._invisible_fields_display.setModel(invisible_fields_model)
        self._visible_fields_display.setModel(visible_fields_model)
        # this has automatically created selection models, TODO possible delete old selection model
        
        self._invisible_fields_selection_model = self._invisible_fields_display.selectionModel()
        self._visible_fields_selection_model = self._visible_fields_display.selectionModel()
    
        self._invisible_fields_selection_model.selectionChanged.connect(self._on_new_invisible_selection)
        self._visible_fields_selection_model.selectionChanged.connect(self._on_new_visible_selection)

    # Get the currently selected row, or None if there is no selection
    def get_invisible_fields_selected_row(self):
        if self._invisible_fields_selection_model is None:
            return None

        sel_rows = self._invisible_fields_selection_model.selectedRows()
        assert len(sel_rows) <= 1
        if len(sel_rows) == 0:
            return None
        else:
            return sel_rows[0].row()

    def get_visible_fields_selected_row(self):
        if self._visible_fields_selection_model is None:
            return None

        sel_rows = self._visible_fields_selection_model.selectedRows()
        assert len(sel_rows) <= 1
        if len(sel_rows) == 0:
            return None
        else:
            return sel_rows[0].row()

    
    ############# Internal Implementation #############

    def _on_new_invisible_selection(self):
        print('Field choice: new invisible selection')
        self._update_button_status()

    def _on_new_visible_selection(self):
        print('Field choice: new visible selection')
        self._update_button_status()

    def _slot_add_button_clicked(self):
        self.add_button_clicked.emit()
        # required since the selection has moved
        self._update_button_status()

    def _slot_remove_button_clicked(self):
        self.remove_button_clicked.emit()
        # required since the selection has moved
        self._update_button_status()

    def _slot_up_button_clicked(self):
        self.up_button_clicked.emit()
        # required since the selection has moved
        self._update_button_status()

    def _slot_down_button_clicked(self):
        self.down_button_clicked.emit()
        # required since the selection has moved
        self._update_button_status()

    def _update_button_status(self):
        # disable everything if any model is missing
        if (
                self._invisible_fields_display.model() is None or self._invisible_fields_selection_model is None or 
                self._visible_fields_display.model() is None or self._visible_fields_selection_model is None ):
            self._add_button.setEnabled(False)
            self._remove_button.setEnabled(False)
            self._up_button.setEnabled(False)
            self._down_button.setEnabled(False)
            return

        # check in detail 
        inv_selected_row = self.get_invisible_fields_selected_row()
        inv_row_count = self._invisible_fields_display.model().rowCount(QtCore.QModelIndex())
        vis_selected_row = self.get_visible_fields_selected_row()
        vis_row_count = self._visible_fields_display.model().rowCount(QtCore.QModelIndex())

        self._add_button.setEnabled(inv_selected_row is not None)
        self._remove_button.setEnabled(vis_selected_row is not None)

        self._up_button.setEnabled(vis_selected_row is not None and vis_selected_row > 0)
        self._down_button.setEnabled(vis_selected_row is not None and vis_selected_row < vis_row_count-1)
