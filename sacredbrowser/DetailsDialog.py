from . import BrowserState

from PyQt5 import QtCore, QtGui, QtWidgets

import re
import os



# This is the dialog which displays details about a single experiment instance.
class DetailsDialog(QtWidgets.QDialog):

    def __init__(self,app,experiment,grid_fs):
        super(DetailsDialog,self).__init__()
        self._app = app
        self._experiment = experiment
        self._grid_fs = grid_fs

        self._make_layout()

        self._make_config_model()
        self._make_entry_model()
        self._make_files_model()

        # bottom button
        self.ok_button.clicked.connect(self.accept)

    def _make_layout(self):
        # widgets 
        self.config_label = QtWidgets.QLabel('Configuration')
        self.config_list = QtWidgets.QListView()
        self.config_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.config_display = QtWidgets.QTextEdit()
        self.config_display.setReadOnly(True)
        
        self.entry_label = QtWidgets.QLabel('Database Entry')
        self.entry_list = QtWidgets.QListView()
        self.entry_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.entry_display = QtWidgets.QTextEdit()
        self.entry_display.setReadOnly(True)

        self.files_label = QtWidgets.QLabel('Attached Files')
        self.files_list = QtWidgets.QListView()
        self.files_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.preview_file_button = QtWidgets.QPushButton('&Preview')
        self.save_file_button = QtWidgets.QPushButton('&Save')

        self.ok_button = QtWidgets.QPushButton('&OK')
                
        self.main_layout = QtWidgets.QGridLayout()

        self.main_layout.addWidget(self.config_label,0,0,1,2)
        self.main_layout.addWidget(self.config_list,1,0)
        self.main_layout.addWidget(self.config_display,1,1)

        self.main_layout.addWidget(self.entry_label,2,0,1,2)
        self.main_layout.addWidget(self.entry_list,3,0)
        self.main_layout.addWidget(self.entry_display,3,1)

        self.main_layout.addWidget(self.files_label,4,0,1,2)
        self.main_layout.addWidget(self.files_list,5,0,1,2)
        self.main_layout.addWidget(self.preview_file_button,6,0)
        self.main_layout.addWidget(self.save_file_button,6,1)

        self.main_layout.addWidget(self.ok_button,7,0,1,2)

        self.setLayout(self.main_layout)

    def _make_config_model(self):
        # model 
        self.config_model = QtGui.QStandardItemModel()
        self.config_list.setModel(self.config_model)

        # iterate over config keys, fill model
        for key in sorted(self._experiment.get_config_fields()):
            item = QtGui.QStandardItem(key)
            item.setEditable(False)
            self.config_model.appendRow(item)

        self.config_list.selectionModel().currentChanged.connect(self._slot_show_config_data)
        self.config_list.selectionModel().select(self.config_model.createIndex(0,0),QtCore.QItemSelectionModel.Select)

    def _make_entry_model(self):
        # model 
        self.entry_model = QtGui.QStandardItemModel()
        self.entry_list.setModel(self.entry_model)

        # iterate over entry keys, fill model
        for key in sorted(self._experiment.get_details().keys()):
            item = QtGui.QStandardItem(key)
            item.setEditable(False)
            self.entry_model.appendRow(item)

        self.entry_list.selectionModel().currentChanged.connect(self._slot_show_entry_data)
        self.entry_list.selectionModel().select(self.entry_model.createIndex(0,0),QtCore.QItemSelectionModel.Select)

    def _make_files_model(self):
        pass
#         self.filesModel = QtGui.QStandardItemModel()
#         self.filesList.setModel(self.filesModel)
# 
#         self.filesList.activated.connect(self.slotDisplayPreview)
# 
#         # iterate over entry keys, fill model
#         if self.currentGridFs is not None:
#             # for artifact filenames, filter for id
#             desiredId = entry['_id']
#             # for sources, requires md hash
#             # TODO this assumes that all sources are mentioned, and may fail when sacred changes!!!
#             sourceList = entry['sources']
#             sourceDict = { e[0]: e[1] for e in sourceList }
# 
#             for fn in sorted(self.currentGridFs.list()):
#                 if re.match(r'^artifact://',fn):
#                     (expname,thisId,thisFilename) = re.match(r'^artifact://([^/]*)/([^/]*)/(.*)$',fn).groups()
#                     if str(thisId) != str(desiredId):
#                         continue # this artifact does not belong to this instance
#                     # TODO add error handling?
#                     displayName = 'Artifact: ' + thisFilename
#                     gridSearchCondition = { 'filename': fn } # TODO parse experimententry for artifact info?
#                     origFilename = thisFilename
#                 else:
#                     if fn in sourceDict:
#                         md5Hash = sourceDict[fn] 
#                         displayName = str(fn)
#                         gridSearchCondition = { 'filename': fn, 'md5': md5Hash } 
#                         origFilename = os.path.basename(displayName)
#                     elif os.path.basename(fn) in sourceDict: # TODO FIXME XXX awful hack
#                         shortFn = os.path.basename(fn)
#                         md5Hash = sourceDict[shortFn] 
#                         displayName = str(shortFn)
#                         gridSearchCondition = { 'filename': fn, '_id': md5Hash }  # HACK HERE
#                         origFilename = os.path.basename(displayName)
#                     else:
#                         continue
# 
#                 item = FileItem(displayName,gridSearchCondition,origFilename)
#                 item.setEditable(False)
#                 self.filesModel.appendRow(item)
# 
#             self.previewFileButton.clicked.connect(self._slot_preview_button_clicked)
#             self.saveFileButton.clicked.connect(self._slot_save_button_clicked)
#             self.previewFileButton.setEnabled(True)
#             self.saveFileButton.setEnabled(True)
#         else:
#             self.previewFileButton.setEnabled(False)
#             self.saveFileButton.setEnabled(False)
# 

    def _slot_show_config_data(self,index):
        this_key = str(self.config_model.data(index))
        this_config_data = self._experiment.get_field((BrowserState.Fields.FieldType.Config,this_key))
        self.config_display.setPlainText(str(this_config_data))

    def _slot_show_entry_data(self,index):
        this_key = str(self.entry_model.data(index))
        this_detail_data = self._experiment.get_details()[this_key]
        self.entry_display.setPlainText(str(this_detail_data))

    def _slot_preview_button_clicked(self):
        self._display_preview()

    def _slot_save_button_clicked(self):
        self._try_save_file()

    def _get_current_file_data(self):
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

    def _display_preview(self):
        data = self._get_current_file_data()

        displayDialog = QtWidgets.QDialog()
        displayDialog.setWindowTitle('Display attachment')

        textField = QtWidgets.QTextEdit()
        textField.setPlainText(data)
        textField.setReadOnly(True)

        saveButton = QtWidgets.QPushButton('&Save')
        saveButton.clicked.connect(self.askAndSaveFile)

        okButton = QtWidgets.QPushButton('&Ok')
        okButton.clicked.connect(displayDialog.accept)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(textField)
        layout.addWidget(saveButton)
        layout.addWidget(okButton)
        displayDialog.setLayout(layout)
        displayDialog.exec_()

    def _try_save_file(self):
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
        saveFileName = QtWidgets.QFileDialog.getSaveFileName(caption='Save file attachment',directory = lastSaveDirectory)

        if len(saveFileName) == 0:
            return #aborted

        dirName = os.path.dirname(str(saveFileName))
        self.application.settings.setValue('Global/lastSaveDirectory',dirName)

        data = self._get_current_file_data()
        fp = open(saveFileName,'wb')
        fp.write(data)
        fp.close()


