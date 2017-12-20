from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from PyQt4 import QtCore, QtGui

import DbTree
import FieldChoiceWidget
import FilterChoice
import ExperimentListView
import StudyModel

# Main window of the application. It is created by the application class and sets up the entire
# visibke interface. Note that signal/slot connections are NOT set up here!
class MainWin(QtGui.QMainWindow):
    def __init__(self,application):
        #Init the base class
        QtGui.QMainWindow.__init__(self, None)
        self.application = application
        self.createWidgets()

    def createWidgets(self):
        # Step 1: create the widgets
        self.dbTree = DbTree.DbTree(self.application)
        self.deleteCurrentDbElement = QtGui.QPushButton('Delete current database element')
        self.connectToDb = QtGui.QPushButton('C&onnect to MongoDb instance')
        self.fieldChoice = FieldChoiceWidget.FieldChoiceWidget()
        self.quickDelete = QtGui.QCheckBox('&Allow delete without confirmation')

        self.resultViewLabel = QtGui.QLabel('Result view mode')

        self.resultViewGroup = QtGui.QButtonGroup() # Grouper for view mode - does not have a visual representation!
        self.resultViewRaw = QtGui.QRadioButton('Raw')
        self.resultViewRounded = QtGui.QRadioButton('Rounded')
        self.resultViewPercent = QtGui.QRadioButton('Percent')

        self.resultViewGroup.addButton(self.resultViewRaw,StudyModel.StudyModel.ResultViewRaw)
        self.resultViewGroup.addButton(self.resultViewRounded,StudyModel.StudyModel.ResultViewRounded)
        self.resultViewGroup.addButton(self.resultViewPercent,StudyModel.StudyModel.ResultViewPercent)

        self.sortButton = QtGui.QPushButton('&Sort Dialog')
        self.sortButton.setCheckable(True)
    
        self.deleteButton = QtGui.QPushButton('&Delete')
        self.copyButton = QtGui.QPushButton('&Copy')
        self.fullEntryButton = QtGui.QPushButton('&Full entry')

        self.filterChoice = FilterChoice.FilterChoice(self.application)
        self.experimentListView = ExperimentListView.ExperimentListView()

        self.resetColWidthButton = QtGui.QPushButton('&Reset column widths')

        self.average = QtGui.QLabel('No data loaded')
        self.average.setSizePolicy ( QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        self.statusbar = QtGui.QStatusBar()
        self.statusbar.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)

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
        # U *        +  3a) "belowCollectionView"
        # T * * * * * * * * * * * * * * * * *
        #   *** Statusbar ***
        #
        # where
        # 1) choice of displayed fields and some commands
        # 2) database filter
        # 3) main view (with some extra command buttons that go below)

        # create part 1
        self.commandsLayout = QtGui.QHBoxLayout()
        self.commandsLayout.addWidget(self.deleteButton)
        self.commandsLayout.addWidget(self.copyButton)
        self.commandsLayout.addWidget(self.fullEntryButton)

        self.resultViewLayout = QtGui.QHBoxLayout()
        self.resultViewLayout.addWidget(self.resultViewLabel)
        self.resultViewLayout.addWidget(self.resultViewRaw)
        self.resultViewLayout.addWidget(self.resultViewRounded)
        self.resultViewLayout.addWidget(self.resultViewPercent)

        # main layout for part 1 
        self.fieldAreaLayout = QtGui.QVBoxLayout()
        self.fieldAreaLayout.addWidget(self.fieldChoice)
        self.fieldAreaLayout.addWidget(self.quickDelete)
        self.fieldAreaLayout.addLayout(self.resultViewLayout)
        self.fieldAreaLayout.addWidget(self.sortButton)
        self.fieldAreaLayout.addLayout(self.commandsLayout)

        self.fieldAreaWidget = QtGui.QWidget()
        self.fieldAreaWidget.setLayout(self.fieldAreaLayout)

        # joint layout for part 1 and 2
        self.upperRightHLayout = QtGui.QSplitter()
        self.upperRightHLayout.addWidget(self.fieldAreaWidget)
        self.upperRightHLayout.addWidget(self.filterChoice)

        self.belowCollectionViewLayout = QtGui.QHBoxLayout()
        self.belowCollectionViewLayout.addWidget(self.average)
        self.belowCollectionViewLayout.addWidget(self.resetColWidthButton)

        self.belowCollectionViewWidget = QtGui.QWidget()
        self.belowCollectionViewWidget.setLayout(self.belowCollectionViewLayout)


        # joint layout for parts 1 to 3 (see above)
        self.rightVLayout = QtGui.QSplitter(QtCore.Qt.Vertical)
        self.rightVLayout.addWidget(self.upperRightHLayout)
        self.rightVLayout.addWidget(self.experimentListView)
        self.rightVLayout.addWidget(self.belowCollectionViewWidget)

        # layout for db tree (left part of the main win)
        self.leftVLayout = QtGui.QVBoxLayout()
        self.leftVLayout.addWidget(self.dbTree)
        self.leftVLayout.addWidget(self.deleteCurrentDbElement)
        self.leftVLayout.addWidget(self.connectToDb)

        self.leftVWidget = QtGui.QWidget()
        self.leftVWidget.setLayout(self.leftVLayout)

        self.mainLayout = QtGui.QSplitter()
        self.mainLayout.addWidget(self.leftVWidget)
        self.mainLayout.addWidget(self.rightVLayout)

        self.topLayout = QtGui.QVBoxLayout()
        self.topLayout.addWidget(self.mainLayout)
        self.topLayout.addWidget(self.statusbar)

        self.centralWidget = QtGui.QWidget()
        self.centralWidget.setLayout(self.topLayout)
        self.setCentralWidget(self.centralWidget)

    # called from the study controller to enable/disable certain GUI elements 
    def enableStudyControls(self,enable):
        self.filterChoice.setEnabled(enable)
        self.fieldChoice.setEnabled(enable)
        self.deleteButton.setEnabled(enable)
        self.copyButton.setEnabled(enable)
        self.fullEntryButton.setEnabled(enable)
        self.resultViewLabel.setEnabled(enable)
        self.resultViewRaw.setEnabled(enable)
        self.resultViewRounded.setEnabled(enable)
        self.resultViewPercent.setEnabled(enable)
        self.experimentListView.setEnabled(enable)
        self.resetColWidthButton.setEnabled(enable)
        self.sortButton.setEnabled(enable)

    # reimplemented to close sort dialog as well
    def closeEvent(self,event):
        
        self.application.sortDialog = None # A HACK TODO
