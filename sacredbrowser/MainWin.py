
from PyQt5 import QtCore, QtGui, QtWidgets

from . import FieldChoiceWidget
from . import FilterChoice
from . import ExperimentListView
from . import StudyModel

# Main window of the application. It is created by the application class and sets up the entire
# visible interface. Note that signal/slot connections are NOT set up here!
class MainWin(QtWidgets.QWidget):
    ############# Signals #############

    window_closed = QtCore.pyqtSignal()

    ############# Main Part #############
    
    def __init__(self,application):
        super().__init__(None)
        self._application = application
        self.create_widgets()

    def create_widgets(self):
        # Step 1: Create the widgets. Note that each widget automatically gets reparented to the containing layout,
        # so dangling references should not appear.
        self.study_tree = QtWidgets.QTreeView()
        self.delete_current_db_element_button = QtWidgets.QPushButton('Delete current database element')
        self.connect_to_db_button = QtWidgets.QPushButton('C&onnect to MongoDb instance')
        self.field_choice = FieldChoiceWidget.FieldChoiceWidget()
        self.quick_delete_button = QtWidgets.QCheckBox('&Allow delete without confirmation')

        self.result_view_group = QtWidgets.QGroupBox('Result display')
        self.result_view_raw = QtWidgets.QRadioButton('Raw')
        self.result_view_round = QtWidgets.QRadioButton('Rounded')
        self.result_view_percent = QtWidgets.QRadioButton('Percent')
        self.result_view_layout = QtWidgets.QHBoxLayout()
        self.result_view_layout.addWidget(self.result_view_raw)
        self.result_view_layout.addWidget(self.result_view_round)
        self.result_view_layout.addWidget(self.result_view_percent)
        self.result_view_group.setLayout(self.result_view_layout)

        self.sort_button = QtWidgets.QPushButton('&Sort Dialog')
        self.sort_button.setCheckable(True)
    
        self.delete_button = QtWidgets.QPushButton('&Delete')
        self.copy_button = QtWidgets.QPushButton('&Copy')
        self.full_entry_button = QtWidgets.QPushButton('&Full entry')

        self.filter_choice = FilterChoice.FilterChoice()
        self.experiment_list_view = ExperimentListView.ExperimentListView()

        self.reset_col_widths_button = QtWidgets.QPushButton('&Reset column widths')

        self.average = QtWidgets.QLabel('No data loaded')
        self.average.setSizePolicy ( QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.statusbar = QtWidgets.QStatusBar()
        self.statusbar.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        # Step 2: create layouts
        # general structure
        #   * * * * * Main layout * * * * * * 
        # T *  Left  +           +
        # O *  Tree  +    1      +     2
        # P *        +           +
        # L *        + + + + + + + + + + + +
        # A *        +
        # Y *        +           3
        # O *        +
        # U *        +  3a) "below_study_view"
        # T * * * * * * * * * * * * * * * * *
        #   *** Statusbar ***
        #
        # where
        # 1) choice of displayed fields and some commands
        # 2) database filter
        # 3) main view (with some extra command buttons that go below)

        # create part 1
        self.commands_layout = QtWidgets.QHBoxLayout()
        self.commands_layout.addWidget(self.delete_button)
        self.commands_layout.addWidget(self.copy_button)
        self.commands_layout.addWidget(self.full_entry_button)

        # main layout for part 1 
        self.field_area_layout = QtWidgets.QVBoxLayout()
        self.field_area_layout.addWidget(self.field_choice)
        self.field_area_layout.addWidget(self.quick_delete_button)
        self.field_area_layout.addWidget(self.result_view_group)
        self.field_area_layout.addWidget(self.sort_button)
        self.field_area_layout.addLayout(self.commands_layout)

        self.field_area_widget = QtWidgets.QWidget()
        self.field_area_widget.setLayout(self.field_area_layout)

        # joint layout for part 1 and 2
        self.upper_splitter = QtWidgets.QSplitter()
        self.upper_splitter.addWidget(self.field_area_widget)
        self.upper_splitter.addWidget(self.filter_choice)

        self.below_study_view_layout = QtWidgets.QHBoxLayout()
        self.below_study_view_layout.addWidget(self.average)
        self.below_study_view_layout.addWidget(self.reset_col_widths_button)

        self.below_study_view_widget = QtWidgets.QWidget()
        self.below_study_view_widget.setLayout(self.below_study_view_layout)


        # joint layout for parts 1 to 3 (see above)
        self.right_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.right_splitter.addWidget(self.upper_splitter)
        self.right_splitter.addWidget(self.experiment_list_view)
        self.right_splitter.addWidget(self.below_study_view_widget)

        # layout for db tree (left part of the main win)
        self.left_layout = QtWidgets.QVBoxLayout()
        self.left_layout.addWidget(self.study_tree)
        self.left_layout.addWidget(self.delete_current_db_element_button)
        self.left_layout.addWidget(self.connect_to_db_button)

        self.left_widget = QtWidgets.QWidget()
        self.left_widget.setLayout(self.left_layout)

        self.main_splitter = QtWidgets.QSplitter()
        self.main_splitter.addWidget(self.left_widget)
        self.main_splitter.addWidget(self.right_splitter)

        self.full_layout = QtWidgets.QVBoxLayout()
        self.full_layout.addWidget(self.main_splitter)
        self.full_layout.addWidget(self.statusbar)

        self.setLayout(self.full_layout)

    # called from the controller to enable/disable certain GUI elements 
    # when a study is loaded
    def enable_study_controls(self,enable):
        self.filter_choice.setEnabled(enable)
        self.field_choice.setEnabled(enable)
        self.delete_button.setEnabled(enable)
        self.copy_button.setEnabled(enable)
        self.full_entry_button.setEnabled(enable)
        self.result_view_group.setEnabled(enable)
        self.experiment_list_view.setEnabled(enable)
        self.reset_col_widths_button.setEnabled(enable)
        self.sort_button.setEnabled(enable)

    # reimplemented to close sort dialog as well
    def closeEvent(self,event):
        
        self.window_closed.emit()
        return super().closeEvent(event)
