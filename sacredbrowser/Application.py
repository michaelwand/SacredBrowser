# TODO add doc!
from . import MainWin
from . import SortDialog
from . import DbEntries
from . import DbController
from . import BrowserState

from PyQt5 import QtCore, QtGui, QtWidgets

import sys
import os

# Main application class, subclassed from QT framework
class Application(QtWidgets.QApplication):
    ############# Initialization #############
    def __init__(self):
        # base constructor
        super(Application, self).__init__(sys.argv)

        # make settings object, read existing settings
        # FIXME only tested on Linux
        self.settings = QtCore.QSettings(os.getenv('HOME') + '/.sacredbrowserrc',QtCore.QSettings.IniFormat)

        # create main window, without functionality
        self._main_win = MainWin.MainWin(self)
        self._main_win.enable_study_controls(False)
        self._main_win.show()

        # prepare database access (does not yet load very much)
        print('Creating connection...')
        self._connection = DbEntries.SacredConnection('mongodb://localhost:27017',self) # TODO make dynamic
        print('Finished creating connection...')

        # create state holders - note that they will be filled by the controller, or possibly also by laoding from the settings
        current_study = BrowserState.CurrentStudy()
        sort_order = BrowserState.SortOrder()
        db_filter = BrowserState.DbFilter()
        fields = BrowserState.Fields()
        general_settings = BrowserState.GeneralSettings()

        self._browser_state = BrowserState.BrowserStateCollection(current_study=current_study,sort_order=sort_order,db_filter=db_filter,fields=fields,general_settings=general_settings)

        # Create controller, merging the GUI and the state objects. Note that the controller connects models to the respective GUI elements
        # and also updates GUI elements directly.
        self._controller = DbController.DbController(self,self._main_win,self._connection,self._browser_state)

        # Connect all slots - everything important should go via the application (why? good question)
        # IMPORTANT REMARK: do not replace the Qt model once set - it would also replace the selection model, and
        # the connections would be broken

        # Study tree
        self._main_win.study_tree.selectionModel().selectionChanged.connect(self._slot_new_study_tree_selection)
        self._main_win.delete_current_db_element_button.clicked.connect(self._slot_delete_db_element)
        self._main_win.connect_to_db_button.clicked.connect(self._slot_connect_to_db)

        # Field choice
        self._main_win.field_choice.add_button_clicked.connect(self._slot_field_choice_add_clicked)
        self._main_win.field_choice.remove_button_clicked.connect(self._slot_field_choice_remove_clicked)
        self._main_win.field_choice.up_button_clicked.connect(self._slot_field_choice_up_clicked)
        self._main_win.field_choice.down_button_clicked.connect(self._slot_field_choice_down_clicked)

        # Filter choice
        self._main_win.filter_choice.new_request.connect(self._slot_new_request)

        # General settings
        self._main_win.result_view_raw.clicked.connect(self._slot_result_view_raw)
        self._main_win.result_view_round.clicked.connect(self._slot_result_view_round)
        self._main_win.result_view_percent.clicked.connect(self._slot_result_view_percent)

        # TODO sort dialog
        self._main_win.sort_button.clicked.connect(self._slot_sort_button_clicked)
        self._main_win.delete_button.clicked.connect(self._slot_delete_clicked)
        
        # Experiment list
        self._main_win.experiment_list_view.delete_requested.connect(self._slot_delete_requested)
        self._main_win.experiment_list_view.copy_requested.connect(self._slot_copy_requested)
        self._main_win.experiment_list_view.full_entry_requested.connect(self._slot_full_entry_requested)

        self._main_win.delete_button.clicked.connect(self._slot_delete_clicked)
        self._main_win.copy_button.clicked.connect(self._slot_copy_clicked)
        self._main_win.full_entry_button.clicked.connect(self._slot_full_entry_clicked)

        self._main_win.experiment_list_view.column_resized.connect(self._slot_column_resized)
        self._main_win.reset_col_widths_button.clicked.connect(self._slot_reset_column_widths_clicked)

    ############# Slots #############
    def _slot_new_study_tree_selection(self):
        self._controller.on_select_sacred_element()

    def _slot_delete_db_element(self):
        QtWidgets.QMessageBox.warning(self,'Not implemented','_slot_delete_db_element not implemented',QtWidgets.QMessageBox.Ok,QtWidgets.QMessageBox.Ok)

    def _slot_connect_to_db(self):
        QtWidgets.QMessageBox.warning(self,'Not implemented','_slot_connect_to_db not implemented',QtWidgets.QMessageBox.Ok,QtWidgets.QMessageBox.Ok)

    def _slot_field_choice_down_clicked(self):
        self._controller.field_down()

    def _slot_field_choice_up_clicked(self):
        self._controller.field_up()

    def _slot_field_choice_add_clicked(self):
        self._controller.field_add()

    def _slot_field_choice_remove_clicked(self):
        self._controller.field_remove()

    def _slot_result_view_raw(self):
        assert self._browser_state.current_study.get_study() is not None
        self._controller.set_view_mode(BrowserState.GeneralSettings.ViewModeRaw)

    def _slot_result_view_round(self):
        assert self._browser_state.current_study.get_study() is not None
        self._controller.set_view_mode(BrowserState.GeneralSettings.ViewModeRounded)

    def _slot_result_view_percent(self):
        assert self._browser_state.current_study.get_study() is not None
        self._controller.set_view_mode(BrowserState.GeneralSettings.ViewModePercent)

    def _slot_new_request(self,text):
        pass

    def _slot_sort_button_clicked(self):
        pass

    def _slot_delete_clicked(self):
        pass

    def _slot_copy_clicked(self):
        pass

    def _slot_full_entry_clicked(self):
        pass

    # slots from the ExperimentListView
    def _slot_delete_requested(self):
        pass

    def _slot_copy_requested(self):
        pass

    def _slot_full_entry_requested(self):
        pass

    def _slot_column_resized(self,col,new_width):
        pass

    def _slot_reset_column_widths_clicked(self):
        pass

        
def run():
    QtCore.pyqtRemoveInputHook() # may be helpful when debugging with pdb
    print('Starting SacredBrowser...')
    app = Application()
#     stylekeys =QtWidgets.QStyleFactory.keys()
    if len(sys.argv) > 1:
        # Windows, Fusion?
        style = sys.argv[1]
        app.setStyle(QtWidgets.QStyleFactory.create(style))
    result = app.exec_()
    return result

