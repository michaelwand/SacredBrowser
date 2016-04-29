from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


from PyQt4 import QtCore, QtGui

# This is the dialog which displays details about a single experiment instance.
class DetailsDialog(QtGui.QDialog):
    def __init__(self,entry):
        super(DetailsDialog,self).__init__()
        self.entry = entry # database entry to be shown

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

        self.okButton = QtGui.QPushButton('&OK')
                
        self.mainLayout.addWidget(self.configLabel,0,0,1,2)
        self.mainLayout.addWidget(self.configList,1,0)
        self.mainLayout.addWidget(self.configDisplay,1,1)
        self.mainLayout.addWidget(self.fieldLabel,2,0,1,2)
        self.mainLayout.addWidget(self.fieldList,3,0)
        self.mainLayout.addWidget(self.fieldDisplay,3,1)
        self.mainLayout.addWidget(self.okButton,4,0,1,2)

        # model for config display
        self.configModel = QtGui.QStandardItemModel()
        self.configList.setModel(self.configModel)

        # iterate over config keys, fill model
        for key in sorted(entry['config'].keys()):
            item = QtGui.QStandardItem(key)
            item.setEditable(False)
            self.configModel.appendRow(item)

        self.configList.selectionModel().currentChanged.connect(self.showConfigData)
        self.configList.selectionModel().select(self.configModel.createIndex(0,0),QtGui.QItemSelectionModel.Select)

        # model for field display
        self.fieldModel = QtGui.QStandardItemModel()
        self.fieldList.setModel(self.fieldModel)

        # iterate over entry keys, fill model
        for key in sorted(entry.keys()):
            item = QtGui.QStandardItem(key)
            item.setEditable(False)
            self.fieldModel.appendRow(item)

        self.fieldList.selectionModel().currentChanged.connect(self.showFieldData)
        self.fieldList.selectionModel().select(self.fieldModel.createIndex(0,0),QtGui.QItemSelectionModel.Select)

        self.okButton.clicked.connect(self.accept)

#         self.fieldList.setCurrentIndex(self.fieldModel.createIndex(0,0))

    def showConfigData(self,index):
        thisKey = str(self.configModel.data(index).toString())
        self.configDisplay.setPlainText(str(self.entry['config'][thisKey]))

    def showFieldData(self,index):
        thisKey = str(self.fieldModel.data(index).toString())
        self.fieldDisplay.setPlainText(str(self.entry[thisKey]))

