

import sys
import os
# import PyQT
from PyQt5 import QtCore, QtGui, QtWidgets

import gridfs

import pymongo # for the error message)

# local imports
from . import MainWin
from . import SortDialog
from . import DbConnection
from . import DbModel
from . import StudyModel
from . import StudyController
from . import ExperimentListModel

# Main application class, subclassed from QT framework
class Application(QtWidgets.QApplication):
    ########################################################
    ## MAIN PART
    ########################################################
    def __init__(self):
        # base constructor
        super(Application, self).__init__(sys.argv)

        # make settings object, read existing settings
        # FIXME only tested on Linux
        self.settings = QtCore.QSettings(os.getenv('HOME') + '/.sacredbrowserrc_temp',QtCore.QSettings.IniFormat)

        # prepare database access (does not do anything)
        self.connection = DbConnection.DbConnection(self)
        self.dbModel = DbModel.DbModel(self)

        # create main window
        self.mainWin = MainWin.MainWin(self)

        # create model and controller for the collection view PLUS associated widgets
        # (i.e. the entire right part of the application window)
        self.experimentListModel = ExperimentListModel.ExperimentListModel(self)

        self.studyModel = StudyModel.StudyModel(self.experimentListModel)
        self.studyController = StudyController.StudyController(self,self.studyModel,self.experimentListModel,self.mainWin.experimentListView,self.mainWin.filterChoice)

        self.mainWin.experimentListView.controller = self.studyController # TODO rename
        self.experimentListModel.controller = self.studyController
        self.studyModel.studyController = self.studyController

        # this order prevents error messages about uninitialized variables?
        self.mainWin.experimentListView.setModel(self.experimentListModel)

        # current database and collection (as pymongo objects)
        self.currentDatabase = None
        self.currentRunCollection = None

        # create non-modal sort dialog
        self.sortDialog = SortDialog.SortDialog(self.studyController)
        self.sortDialog.closeCalled.connect(self.slotSortDialogClosed)

        # connect signals/slots from main window
        self.mainWin.dbTree.selectionModel().currentChanged.connect(self.slotChooseCollection)
# # #         self.mainWin.dbTree.activated.connect(self.slotChooseCollection)
        self.mainWin.deleteCurrentDbElement.clicked.connect(self.slotDeleteCurrentDbElement)
        self.mainWin.connectToDb.clicked.connect(self.slotConnectToMongoDbInstance)

        # subwidgets in the main window
        # TODO inconsistent naming
        self.mainWin.fieldChoice.fieldChoiceChanged.connect(self.studyController.slotFieldSelectionChanged)
        self.mainWin.quickDelete.stateChanged.connect(self.slotAllowQuickDeleteToggled)
        self.mainWin.filterChoice.clearButton.clicked.connect(self.studyController.slotClearSearchClicked)
        self.mainWin.filterChoice.searchButton.clicked.connect(self.studyController.slotDoNewSearchClicked)

        # display settings and controls
        self.mainWin.resultViewGroup.buttonClicked[int].connect(self.studyController.slotResultViewChanged)
        self.mainWin.sortButton.toggled.connect(self.slotSortDialogToggled)
        self.mainWin.deleteButton.clicked.connect(self.studyController.slotDeleteSelection)
        self.mainWin.copyButton.clicked.connect(self.studyController.slotCopyToClipboard)
        self.mainWin.fullEntryButton.clicked.connect(self.studyController.slotFullEntry)
# # # # #         self.mainWin.experimentListView.horizontalHeader().sectionResized.connect(self.studyController.slotSectionResized)
        self.mainWin.resetColWidthButton.clicked.connect(self.studyController.slotResetColWidth)

        self.aboutToQuit.connect(self.finalCleanup)

        # set initial values for check boxes
        lastAllowQuickDelete = self.settings.value('Global/allowQuickDelete',type=bool)
        if lastAllowQuickDelete is not None:
            self.allowQuickDelete = lastAllowQuickDelete
        else:
            self.allowQuickDelete = False
        self.mainWin.quickDelete.setChecked(self.allowQuickDelete)

        self.mainWin.resultViewRaw.setChecked(True)
        self.mainWin.resultViewRounded.setChecked(False)
        self.mainWin.resultViewPercent.setChecked(False)

        self.mainWin.enableStudyControls(False)

        self.mainWin.show()

        self.showStatusMessage('Welcome to SacredAdmin!')

        #### TEMP FIXME TODO ###
#         self.createDbConnection('mongodb://peperoncino.idsia.ch:27017')
        self.createDbConnection('mongodb://localhost:27017')

    # Ask for a database to connect to, and create the connection
    def slotConnectToMongoDbInstance(self):
        uri = self.getDbUri()
        if uri is not None:
            self.createDbConnection(uri)

    def getDbUri(self):
        # example URI: mongodb://localhost:27017
        lastMongoURI = self.settings.value('Global/LastMongoURI')
        if lastMongoURI and lastMongoURI.isValid():
            lastMongoURI = lastMongoURI.toString()
        else:
            lastMongoURI = 'mongodb://localhost:27017'

        (newMongoUri,ok) = QtGui.QInputDialog.getText(None,'Connect to database','Connection URI (example: mongodb://localhost:27017)',QtGui.QLineEdit.Normal,lastMongoURI)
        
        if ok:
            self.settings.setValue('Global/LastMongoURI',str(newMongoUri))
            return str(newMongoUri) 
        else:
            return None

    def createDbConnection(self,uri):
        try:
            self.connection.connect(uri)
        except pymongo.errors.ConnectionFailure as e:
            QtGui.QMessageBox.critical(None,'Could not connect to database',
                    'Database connection could not be established. Pymongo raised error:\n%s' % str(e))

        else:
            self.dbModel.doReset()

            # current database and collection (as pymongo objects)
            self.currentDatabase = None
            self.currentRunCollection = None
            self.currentDatabaseName = None
            self.currentRunCollectionName = None
            self.currentGridFs = None

    # display status message below main window
    def showStatusMessage(self,msg):
        self.mainWin.statusbar.showMessage(msg)

    # final cleanup
    def finalCleanup(self):
#         print('Doing empty final cleanup!')
        pass

    ########################################################
    ## SLOTS
    ########################################################

    # This is called when the user chooses an element of the collection tree on the left side of the main window.
    # If the chosen node does NOT represent a collection, empty out the collection view
    # TODO rename
    def slotChooseCollection(self,index):
        node = index.internalPointer()
        if node.databaseName is not None:
            if node.collectionId is not None:
                # this is an actual collection 
                self.currentDatabaseName = node.databaseName
                self.currentRunCollectionName = node.runCollectionName
                self.currentDatabase = self.connection.getDatabase(node.databaseName)
                self.currentRunCollection = self.connection.getCollection(self.currentDatabase,node.runCollectionName)
                if node.gridCollectionPrefix is not None:
                    self.currentGridFs = gridfs.GridFS(self.currentDatabase,collection=node.gridCollectionPrefix)
                else:
                    self.currentGridFs = None
                self.collectionSettingsName = self.currentDatabase.name + '/' + node.runCollectionName
            else:
                # selected database
                self.currentDatabaseName = node.databaseName
                self.currentRunCollectionName = None
                self.currentDatabase = self.connection.getDatabase(node.databaseName)
                self.currentRunCollection = None
                self.currentGridFs = None
                self.collectionSettingsName = None
        else:
            # maybe the root node?
            self.currentDatabaseName = None
            self.currentRunCollectionName = None
            self.currentDatabase = None
            self.currentRunCollection = None
            self.currentGridFs = None
            self.collectionSettingsName = None

        self.studyController.reset()

    def slotDeleteCurrentDbElement(self):
        raise Exception('This is not completely implemented!')
        indexes = self.mainWin.dbTree.selectedIndexes()
        assert len(indexes) <= 1
        if len(indexes) == 0:
            QtGui.QMessageBox.warning(None,'Error deleting element','Please select and display a database element')
            return

        index = indexes[0]
        node = index.internalPointer()

        if node.databaseName is None:
            QtGui.QMessageBox.warning(None,'Error deleting element','Please select and display a database element')
            return

        # "choose" database
        if node.databaseName != self.currentDatabaseName or node.runCollectionName != self.currentRunCollectionName:
            QtGui.QMessageBox.warning(None,'Error deleting element','Displayed collection and selected collection are not identical. Please reselect the database element to be deleted')
            return

        pass
        if 0:
            reply = QtGui.QMessageBox.warning(None,'Really proceed?','Really delete collection %s and all associated files?' % node.collectionId,QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.No:
                return



    # this is called when the "sort dialog" button is clicked (it depends on the button state whether the
    # dialog is opened or closed
    def slotSortDialogToggled(self,on):
        print('Toggled sort dialog to ',on)

        # main work
        self.sortDialog.setVisible(on)


    # this is called when the sort dialog is made invisible
    def slotSortDialogClosed(self):
        self.mainWin.sortButton.setChecked(False)

    # called when the 'allow delete without confirmation' checkbox was toggled
    def slotAllowQuickDeleteToggled(self,state):
        print('slotAllowQuickDeleteToggled, state',state)
        if state > 0:
            self.allowQuickDelete = True
        else:
            self.allowQuickDelete = False

        # save to settings
        self.settings.setValue('Global/allowQuickDelete',self.allowQuickDelete)


    ########################################################
    ## SIGNALS
    ########################################################
        
def run():
    QtCore.pyqtRemoveInputHook() # may be helpful when debugging with pdb
    print('Starting SacredBrowser...')
    app = Application()
    result = app.exec_()
    return result

