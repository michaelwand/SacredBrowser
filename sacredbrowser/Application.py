# TODO add doc!
from . import MainWin
from . import DbModel
from . import DbEntries
from . import DbController
from . import BrowserState
from . import SortedExperimentList
from . import SortDialog
from . import DetailsDialog

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
        self.settings = QtCore.QSettings(os.getenv('HOME') + '/.sacredbrowserrc_version2',QtCore.QSettings.IniFormat)

        # prepare database access (does not yet load very much)
        self._connection = DbEntries.SacredConnection(self)

        # create state holders - note that they will be filled by the controller, or possibly also by loading from the settings
        self._browser_state = BrowserState.create_browser_state()
        BrowserState.setup_browser_state_connections(self._browser_state)

        # create main window, without functionality
        self._main_win = MainWin.MainWin(self,self._browser_state)
        self._main_win.enable_study_controls(False)
        self._main_win.show()

        # sorted experiment list, somewhat intermediate between browser state and controller/models
        self._sorted_experiment_list = SortedExperimentList.SortedExperimentList(self._browser_state)

        # Create controller, allowing interaction between the GUI and the state objects. Note that the controller connects models to the respective GUI elements
        # and also updates GUI elements directly.
        self._controller = DbController.DbController(self,self._main_win,self._connection,self._browser_state,self._sorted_experiment_list)

        # Placeholder for sort dialog
        self._sort_dialog = None
        self._main_win.sort_button.setChecked(False)

        # finish by setting up the slot connections from buttons etc. to the application (which usually forwards that to the controller)
        self._setup_main_win_connections()

    def _setup_main_win_connections(self):
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
        self._main_win.filter_choice.new_query.connect(self._slot_new_query)

        # General settings
        self._main_win.result_view_raw.clicked.connect(self._slot_result_view_raw)
        self._main_win.result_view_round.clicked.connect(self._slot_result_view_round)
        self._main_win.result_view_percent.clicked.connect(self._slot_result_view_percent)

#         self._browser_state.general_settings.column_width_changed.connect(self._slot_column_width_changed)

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

        # Close entire application with main window
        self._main_win.window_closed.connect(self.quit)

    ############# "Global" data #############
    @staticmethod
    def get_global_settings():
        app = QtCore.QCoreApplication.instance()
        return app.settings

    ############# Implementation #############

    def _try_delete_experiment(self):
        # Get selection info and ask
        indexes = self._main_win.experiment_list_view.selectedIndexes()
        if len(indexes) == 0:
            return

        rows = set([x.row() for x in indexes])
        reply = QtWidgets.QMessageBox.warning(None,'Really proceed?','Delete %d experiments?' % len(rows),QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.No:
            return

        print('Application tries to delete experiments at rows',rows)

        # get object IDs from selection
        experiment_list_model = self._controller.get_experiment_list_model()
        experiments = { experiment_list_model.data(idx,DbModel.SacredItemRole) for idx in indexes }

        ob_ids = { exp.id() for exp in experiments }

        print('Application tries to delete experiments with ids',ob_ids)

        self._controller.delete_experiments(ob_ids)

    def _copy_experiment_data(self):
        indexes = self._main_win.experiment_list_view.selectedIndexes()
        print('Call to _copy_experiment_data')

        if len(indexes) == 0:
            return

        # sort: first row, then column
        sort_key = lambda ind: (ind.row(),ind.column())
        indexes.sort(key=sort_key)
        
        # minimum column for proper alignment
        min_col = min([ind.column() for ind in indexes])

        # now make CSV. Count rows for status message.
        cur_row = indexes[0].row()
        cur_col = min_col
        text_result = ''
        all_rows = set()
        for ind in indexes:
            this_row = ind.row()
            this_col = ind.column()
            this_data = str(self._controller.get_experiment_list_model().data(ind,QtCore.Qt.DisplayRole))
            assert this_row >= cur_row
            for rowX in range(cur_row,this_row):
                text_result += '\n'
                cur_col = min_col # reset at new line
            cur_row = this_row
            for colX in range(cur_col,this_col):
                text_result += ','
            cur_col = this_col

            text_result += this_data
            all_rows.add(this_row)

        # copy that
        self.clipboard().setText(text_result)
# # #         self.getApplication().showStatusMessage('Copied %d cells from %d entries.' % (len(indexes),len(allRows)))


    def _show_experiment_details(self):
        indexes = self._main_win.experiment_list_view.selectedIndexes()
        rows = set([x.row() for x in indexes])
        if len(rows) != 1:
            QtWidgets.QMessageBox.warning(None,'Cannot show details','%d rows of experiments selected. Please select exactly one row of experiments' % len(rows),QtWidgets.QMessageBox.Ok,QtWidgets.QMessageBox.Ok)

        any_index = next(iter(indexes))

        # set up and show details dialog
        experiment_list_model = self._controller.get_experiment_list_model()
        experiment = experiment_list_model.data(any_index,DbModel.SacredItemRole)
        grid_fs = experiment.get_study().get_filesystem()

        details_dialog = DetailsDialog.DetailsDialog(self,experiment,grid_fs)

        details_dialog.exec_()

    ############# Slots #############

    # slots from buttons which affect the display
    def _slot_new_study_tree_selection(self):
        self._controller.on_select_sacred_element()

    def _slot_delete_db_element(self):
        selected_indexes = self._main_win.study_tree.selectedIndexes()
        assert len(selected_indexes) <= 1
        if len(selected_indexes) == 0:
            return
        
        sacred_item = self._controller._study_tree_model.sacred_from_index(selected_indexes[0])
        print('Now trying to delete element %s with type %s' % (sacred_item,sacred_item.typename()) )
        if sacred_item.typename() == 'SacredDatabase':
            self._controller.delete_database(sacred_item)
        elif sacred_item.typename() == 'SacredStudy':
            self._controller.delete_study(sacred_item)

    def _slot_connect_to_db(self):
        last_uri = self.settings.value('Global/lastMongoUri')
        if last_uri is None:
            last_uri = 'mongodb://localhost:27017'
        new_uri, okPressed = QtWidgets.QInputDialog.getText(None, 'Create mongo connection','Mongo URI:', QtWidgets.QLineEdit.Normal, last_uri)
        if okPressed and new_uri != '':
            self._connection.connect(new_uri)
            # TODO and on error?
            self.settings.setValue('Global/lastMongoUri',new_uri)

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

    def _slot_new_query(self,text):
        self._controller.new_query(text)

    def _slot_sort_button_clicked(self):
        # open/close sort dialog, change button
        if self._sort_dialog is None:
            self._sort_dialog = SortDialog.SortDialog(self._browser_state.sort_order)
            self._sort_dialog.sort_request.connect(self._slot_sort_request) # will disconnect automagically when dialog closes
            self._sort_dialog.dialog_closed.connect(self._slot_sort_dialog_closed)
            self._main_win.sort_button.setChecked(True)
        else:
            self._sort_dialog.hide() # as far as the user is concerned
            self._sort_dialog.deleteLater()
            self._sort_dialog = None
            self._main_win.sort_button.setChecked(False)

    # slots pertaining to the experiment list view
    def _slot_delete_clicked(self):
        self._try_delete_experiment()

    def _slot_copy_clicked(self):
        self._copy_experiment_data()

    def _slot_full_entry_clicked(self):
        self._show_experiment_details()

    # slot from sort dialog
    def _slot_sort_request(self,field,pos):
        self._controller.sort_request(field,pos)

    # slots from the ExperimentListView
    def _slot_delete_requested(self):
        self._try_delete_experiment()

    def _slot_copy_requested(self):
        self._copy_experiment_data()

    def _slot_full_entry_requested(self):
        self._show_experiment_details()

    # signal from user action
    def _slot_column_resized(self,col,new_width):
        col_name = self._browser_state.fields.get_visible_fields()[col]
        self._browser_state.general_settings.column_width_changed_by_user(col_name,new_width)

    def _slot_reset_column_widths_clicked(self):
        self._browser_state.general_settings.reset_column_widths()

#     # signal from browser_state (not emitted when column width change was result of user action)
#     def _slot_column_width_changed(self,col_name,new_width):
#         try:
#             col_idx = self._browser_state.fields.get_visible_fields().index(col_name)
#         except ValueError:
#             print('BAD - column with name %s not found,, sync issue???' % col_name)
# 
#         print('GOOD - column %d with name %s and width %d, setting' % (col_idx,col_name,new_width))
#         self.experiment_list_view.setColumnWidth(col_idx,new_width)

    # close signal from the non-modal sort dialog
    def _slot_sort_dialog_closed(self):
        self._sort_dialog.deleteLater()
        self._sort_dialog = None
        self._main_win.sort_button.setChecked(False)


        
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

