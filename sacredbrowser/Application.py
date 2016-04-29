from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


import sys
import os
# import PyQT
from PyQt4 import QtCore, QtGui

# local imports
import MainWin
import SortDialog
import DbConnection
import DbModel
import CollectionModel

# Main application class, subclassed from QT framework
class Application(QtGui.QApplication):
    ########################################################
    ## MAIN PART
    ########################################################
    def __init__(self):
        # base constructor
        super(Application, self).__init__(sys.argv)

        # make settings object, read existing settings
        # FIXME only tested on Linux
        self.settings = QtCore.QSettings(os.getenv('HOME') + '/.sacredbrowserrc',QtCore.QSettings.IniFormat)

        # prepare database access (does not do anything)
        self.connection = DbConnection.DbConnection(self)
        self.dbModel = DbModel.DbModel(self)
        self.collectionModel = CollectionModel.CollectionModel(self)

        # current database and collection (as pymongo objects)
        self.currentDatabase = None
        self.currentCollection = None

        # create main window
        self.mainWin = MainWin.MainWin(self)
        self.mainWin.show()

        # create non-modal sort dialog
        self.sortDialog = SortDialog.SortDialog()
        self.sortDialog.closeCalled.connect(self.slotSortDialogClosed)

        # connect signals/slots from main window
        self.mainWin.dbTree.activated.connect(self.slotChooseCollection)
        self.mainWin.connectToDb.clicked.connect(self.slotConnectToDatabase)

        # subwidgets in the main window
        self.mainWin.fieldChoice.fieldChoiceChanged.connect(self.collectionModel.slotFieldSelectionChanged)
        self.mainWin.quickDelete.stateChanged.connect(self.collectionModel.slotAllowQuickDeleteToggled)
        self.sortDialog.sortOrderChanged.connect(self.collectionModel.slotSortOrderChanged)
        self.mainWin.filterChoice.doNewSearch.connect(self.collectionModel.slotDoNewSearch)

        # display settings and controls
        self.mainWin.resultViewGroup.buttonClicked[int].connect(self.collectionModel.slotResultViewChanged)
        self.mainWin.sortButton.toggled.connect(self.slotSortDialogToggled)
        self.mainWin.deleteButton.clicked.connect(self.collectionModel.slotDeleteSelection)
        self.mainWin.copyButton.clicked.connect(self.collectionModel.slotCopyToClipboard)
        self.mainWin.fullEntryButton.clicked.connect(self.collectionModel.slotFullEntry)
        self.mainWin.collectionView.horizontalHeader().sectionResized.connect(self.collectionModel.slotSectionResized)
        self.mainWin.resetColWidthButton.clicked.connect(self.collectionModel.slotResetColWidth)

        self.aboutToQuit.connect(self.finalCleanup)

        # set initial values for check boxes
        quickDeleteChecked = self.settings.value('Global/quickDeleteChecked')
        if quickDeleteChecked.isValid():
            self.mainWin.quickDelete.setChecked(quickDeleteChecked.toBool())

        self.mainWin.resultViewRaw.setChecked(True)
        self.mainWin.resultViewRounded.setChecked(False)
        self.mainWin.resultViewPercent.setChecked(False)

        self.showStatusMessage('Welcome to SacredAdmin!')

    # connect to a database - can also be called directly when starting?
    def slotConnectToDatabase(self):
        if self.connection.connect():
            print('Accessing database')
            # reset everything
            self.dbModel.doReset()

            # current database and collection (as pymongo objects)
            self.currentDatabase = None
            self.currentCollection = None

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

    # this is called when the user chooses a mongodb collection 
    def slotChooseCollection(self,index):
        node = index.internalPointer()
        if node.collectionInfo is not None:
            # chose a collection
            self.currentDatabase = self.connection.getDatabase(node.collectionInfo[0])
            self.currentCollection = self.connection.getCollection(self.currentDatabase,node.collectionInfo[1])
            self.collectionSettingsName = self.currentDatabase.name + '/' + self.currentCollection.name
            self.collectionModel.resetCollection()

    # this is called when the "sort dialog" button is clicked (it depends on the button state whether the
    # dialog is opened or closed
    def slotSortDialogToggled(self,on):
        print('Toggled sort dialog to ',on)

        # main work
        self.sortDialog.setVisible(on)


    # this is called when the sort dialog is made invisible
    def slotSortDialogClosed(self):
        self.mainWin.sortButton.setChecked(False)

    ########################################################
    ## SIGNALS
    ########################################################
        
def run():
    QtCore.pyqtRemoveInputHook() # may be helpful when debugging with pdb
    print('Starting SacredBrowser...')
    app = Application()
    result = app.exec_()
    return result

