from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import re
import os

from PyQt4 import QtCore, QtGui

# slight extension to QStandardItem, with extra parameters: The search condition for the
# gridfs, and the original filename (this should be the filename where the data was taken from,
# without path, suitable for the QFileDialog)
class FileItem(QtGui.QStandardItem):
    def __init__(self,visibleText,gridSearchCondition,origFilename):
        super(FileItem,self).__init__(visibleText)
        self.gridSearchCondition = gridSearchCondition
        self.origFilename = origFilename

# This is the dialog which displays details about a single experiment instance.
class DetailsDialog(QtGui.QDialog):
    def __init__(self,application,entry,currentGridFs):
        super(DetailsDialog,self).__init__()
        self.application = application #I don't like that 
        self.entry = entry # database entry to be shown
        self.currentGridFs = currentGridFs

        # main layout, refilled whenever something changes
        self.mainLayout = QtGui.QGridLayout()
        self.setLayout(self.mainLayout)

        # widgets 
        self.configLabel = QtGui.QLabel('Configuration')
        self.configList = QtGui.QListView()
        self.configList.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.configDisplay = QtGui.QTextEdit()
        self.configDisplay.setReadOnly(True)
        
        self.fieldLabel = QtGui.QLabel('Full Entry')
        self.fieldList = QtGui.QListView()
        self.fieldList.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.fieldDisplay = QtGui.QTextEdit()
        self.fieldDisplay.setReadOnly(True)

        self.filesLabel = QtGui.QLabel('Attached Files')
        self.filesList = QtGui.QListView()
        self.filesList.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.previewFileButton = QtGui.QPushButton('&Preview')
        self.saveFileButton = QtGui.QPushButton('&Save')

        self.okButton = QtGui.QPushButton('&OK')
                
        self.mainLayout.addWidget(self.configLabel,0,0,1,2)
        self.mainLayout.addWidget(self.configList,1,0)
        self.mainLayout.addWidget(self.configDisplay,1,1)

        self.mainLayout.addWidget(self.fieldLabel,2,0,1,2)
        self.mainLayout.addWidget(self.fieldList,3,0)
        self.mainLayout.addWidget(self.fieldDisplay,3,1)

        self.mainLayout.addWidget(self.filesLabel,4,0,1,2)
        self.mainLayout.addWidget(self.filesList,5,0,1,2)
        self.mainLayout.addWidget(self.previewFileButton,6,0)
        self.mainLayout.addWidget(self.saveFileButton,6,1)

        self.mainLayout.addWidget(self.okButton,7,0,1,2)

        # CONFIGURATION display

        # model 
        self.configModel = QtGui.QStandardItemModel()
        self.configList.setModel(self.configModel)

        # iterate over config keys, fill model
        for key in sorted(entry['config'].keys()):
            item = QtGui.QStandardItem(key)
            item.setEditable(False)
            self.configModel.appendRow(item)

        self.configList.selectionModel().currentChanged.connect(self.slotShowConfigData)
        self.configList.selectionModel().select(self.configModel.createIndex(0,0),QtGui.QItemSelectionModel.Select)

        # FIELD display

        # model for field display
        self.fieldModel = QtGui.QStandardItemModel()
        self.fieldList.setModel(self.fieldModel)

        # iterate over entry keys, fill model
        for key in sorted(entry.keys()):
            item = QtGui.QStandardItem(key)
            item.setEditable(False)
            self.fieldModel.appendRow(item)

        self.fieldList.selectionModel().currentChanged.connect(self.slotShowFieldData)
        self.fieldList.selectionModel().select(self.fieldModel.createIndex(0,0),QtGui.QItemSelectionModel.Select)

        # FILES display

        # model for field display
        self.filesModel = QtGui.QStandardItemModel()
        self.filesList.setModel(self.filesModel)

        self.filesList.activated.connect(self.slotDisplayPreview)

        # iterate over entry keys, fill model
        if self.currentGridFs is not None:
            # for artifact filenames, filter for id
            desiredId = entry['_id']
            # for sources, requires md hash
            # TODO this assumes that all sources are mentioned, and may fail when sacred changes!!!
            sourceList = entry['sources']
            sourceDict = { e[0]: e[1] for e in sourceList }

            for fn in sorted(self.currentGridFs.list()):
                if re.match(r'^artifact://',fn):
                    (expname,thisId,thisFilename) = re.match(r'^artifact://([^/]*)/([^/]*)/(.*)$',fn).groups()
                    if str(thisId) != str(desiredId):
                        continue # this artifact does not belong to this instance
                    # TODO add error handling?
                    displayName = 'Artifact: ' + thisFilename
                    gridSearchCondition = { 'filename': fn } # TODO parse experimententry for artifact info?
                    origFilename = thisFilename
                else:
                    if fn not in sourceDict:
                        continue # this is not a source for this particular instance
                    md5Hash = sourceDict[fn] 
                    # error handling TODO
                    displayName = str(fn)
                    gridSearchCondition = { 'filename': fn, 'md5': md5Hash } 
                    origFilename = os.path.basename(displayName)
                item = FileItem(displayName,gridSearchCondition,origFilename)
                item.setEditable(False)
                self.filesModel.appendRow(item)

            self.previewFileButton.clicked.connect(self.slotPreviewButtonClicked)
            self.saveFileButton.clicked.connect(self.slotSaveButtonClicked)
            self.previewFileButton.setEnabled(True)
            self.saveFileButton.setEnabled(True)
        else:
            self.previewFileButton.setEnabled(False)
            self.saveFileButton.setEnabled(False)

        # bottom button
        self.okButton.clicked.connect(self.accept)

#         self.fieldList.setCurrentIndex(self.fieldModel.createIndex(0,0))

    def slotShowConfigData(self,index):
        thisKey = str(self.configModel.data(index).toString())
        self.configDisplay.setPlainText(str(self.entry['config'][thisKey]))

    def slotShowFieldData(self,index):
        thisKey = str(self.fieldModel.data(index).toString())
        self.fieldDisplay.setPlainText(str(self.entry[thisKey]))

    def slotPreviewButtonClicked(self):
        self.slotDisplayPreview()

    def slotSaveButtonClicked(self):
        self.askAndSaveFile()

    def getCurrentFileData(self):
        theIndex = self.filesList.currentIndex()
        assert theIndex.isValid()
        theItem = self.filesModel.itemFromIndex(theIndex)
        theText = theItem.text()
        gridSearchCondition = theItem.gridSearchCondition

        gridList = list(self.currentGridFs.find(gridSearchCondition))
        assert len(gridList) >= 1
        if len(gridList) > 1:
            # TODO
            print('Error: call to %s yields %d results, expected exactly one!' % (str(gridSearchCondition),len(gridList)))
        return gridList[0].read()

    def slotDisplayPreview(self):
        data = self.getCurrentFileData()

        displayDialog = QtGui.QDialog()
        displayDialog.setWindowTitle('Display attachment')

        textField = QtGui.QTextEdit()
        textField.setPlainText(data)
        textField.setReadOnly(True)

        saveButton = QtGui.QPushButton('&Save')
        saveButton.clicked.connect(self.askAndSaveFile)

        okButton = QtGui.QPushButton('&Ok')
        okButton.clicked.connect(displayDialog.accept)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(textField)
        layout.addWidget(saveButton)
        layout.addWidget(okButton)
        displayDialog.setLayout(layout)
        displayDialog.exec_()

    def askAndSaveFile(self):
        lastSaveDirectory = self.application.settings.value('Global/lastSaveDirectory')
        if not (lastSaveDirectory and lastSaveDirectory.isValid()):
            lastSaveDirectory = os.getcwd()
        else:
            lastSaveDirectory = str(lastSaveDirectory.toString())

        # get the file name
        theIndex = self.filesList.currentIndex()
        assert theIndex.isValid()
        theItem = self.filesModel.itemFromIndex(theIndex)
        origFilename = theItem.origFilename

        lastSaveDirectory = os.path.join(lastSaveDirectory,origFilename)
        saveFileName = QtGui.QFileDialog.getSaveFileName(caption='Save file attachment',directory = lastSaveDirectory)

        if len(saveFileName) == 0:
            return #aborted

        dirName = os.path.dirname(str(saveFileName))
        self.application.settings.setValue('Global/lastSaveDirectory',dirName)

        data = self.getCurrentFileData()
        fp = open(saveFileName,'wb')
        fp.write(data)
        fp.close()


