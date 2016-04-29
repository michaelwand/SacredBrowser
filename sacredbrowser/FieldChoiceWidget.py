from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


from PyQt4 import QtCore, QtGui
import sys

# This class implements a widget consisting of two lists. The first one contains a selection of 
# available items, the right one a (sorted) list of chosen items. Items may be moved between the lists,
# as well as sorted within the list of chosen items.
class FieldChoiceWidget(QtGui.QWidget):

    ########################################################
    ## SIGNALS
    ########################################################
      
    fieldChoiceChanged = QtCore.pyqtSignal(list, name='fieldChoiceChanged')

    ########################################################
    ## MAIN PART
    ########################################################

    def __init__(self):
        super(FieldChoiceWidget,self).__init__()
        self.setSizePolicy (QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Expanding)

        # FIXME TODO debug only
#         p = self.palette()
#         p.setColor(self.backgroundRole(), QtCore.Qt.red)
#         self.setPalette(p)
#         self.setAutoFillBackground(True)

        # make submodels - they are filled when reset() is called
        self.availableFields = QtGui.QStandardItemModel()
        self.selectedFields = QtGui.QStandardItemModel()

        # make subwidgets
        self.availableFieldsDisplay = QtGui.QListView()
        self.availableFieldsDisplay.setModel(self.availableFields)
        self.availableFieldsDisplay.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.availableFieldsDisplay.setSizePolicy(QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Expanding)


        self.selectedFieldsDisplay = QtGui.QListView()
        self.selectedFieldsDisplay.setModel(self.selectedFields)
        self.selectedFieldsDisplay.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.selectedFieldsDisplay.setSizePolicy(QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Expanding)
      
        self.addButton = QtGui.QPushButton('+')
        self.addButton.setSizePolicy(QtGui.QSizePolicy.Preferred,QtGui.QSizePolicy.Expanding)
        self.removeButton = QtGui.QPushButton('-')
        self.removeButton.setSizePolicy(QtGui.QSizePolicy.Preferred,QtGui.QSizePolicy.Expanding)
        self.upButton = QtGui.QPushButton('UP')
        self.upButton.setSizePolicy(QtGui.QSizePolicy.Preferred,QtGui.QSizePolicy.Expanding)
        self.downButton = QtGui.QPushButton('DOWN')
        self.downButton.setSizePolicy(QtGui.QSizePolicy.Preferred,QtGui.QSizePolicy.Expanding)

        # connect
        self.addButton.clicked.connect(self.slotAddButtonClicked)
        self.removeButton.clicked.connect(self.slotRemoveButtonClicked)
        self.upButton.clicked.connect(self.slotUpButtonClicked)
        self.downButton.clicked.connect(self.slotDownButtonClicked)
        self.selectedFieldsDisplay.selectionModel().currentChanged.connect(self.slotUpdateButtonStatus)

        # make layout
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.availableFieldsDisplay,0,0,2,1)
        self.layout.addWidget(self.addButton,0,1,1,1)
        self.layout.addWidget(self.removeButton,1,1,1,1)
      
        self.layout.addWidget(self.selectedFieldsDisplay,0,2,2,1)
        self.layout.addWidget(self.upButton,0,3,1,1)
        self.layout.addWidget(self.downButton,1,3,1,1)

        self.setLayout(self.layout)

        # update button status (should disable everything)
        self.updateButtonStatus()

    # Called when a new data collection is displayed. The data is passed in as text
    def reset(self,newAvailableTexts,newSelectedTexts):
        # precheck
        for txt in newAvailableTexts:
            assert type(txt) == unicode
        for txt in newSelectedTexts:
            assert txt in newAvailableTexts

        # empty old info
        self.availableFields.clear()
        self.selectedFields.clear()

        # fill model
        for txt in newAvailableTexts:
            # note that we will emit fieldChoiceChanged afterwards, for the list view
            item = QtGui.QStandardItem(txt)
            item.setEditable(False)
            # CAUTION!
            if txt in newSelectedTexts:
                #  Bad for order
                # self.selectedFields.appendRow(item)
                pass
            else:
                self.availableFields.appendRow(item)

        for txt in newSelectedTexts:
            item = QtGui.QStandardItem(txt)
            item.setEditable(False)
            self.selectedFields.appendRow(item)

        # update widgets
        if self.availableFields.hasIndex(0,0):
            self.availableFieldsDisplay.setCurrentIndex(self.availableFields.indexFromItem(self.availableFields.item(0)))

        if self.selectedFields.hasIndex(0,0):
            self.selectedFieldsDisplay.setCurrentIndex(self.selectedFields.indexFromItem(self.selectedFields.item(0)))

        self.updateButtonStatus()

        self.fieldChoiceChanged.emit(self.getCurrentSelectedFields())

    # returns a list of currently selected fields (i.e. what we actually care about)
    def getCurrentSelectedFields(self):
        result = []
        for i in range(self.selectedFields.rowCount()):
            theItem = self.selectedFields.item(i)
            theText = theItem.text()
            result.append(theText)
        return result

    # update the enabledness of the buttons
    def updateButtonStatus(self):
        if self.availableFields.hasIndex(0,0): # ... is not empty
            self.addButton.setEnabled(True)
        else:
            self.addButton.setEnabled(False)

        if self.selectedFields.hasIndex(0,0):
            self.removeButton.setEnabled(True)
        else:
            self.removeButton.setEnabled(False)

        theIndex = self.selectedFieldsDisplay.currentIndex()
        if theIndex.isValid():
            self.upButton.setEnabled(theIndex.row() > 0)
            self.downButton.setEnabled(theIndex.row() < self.selectedFields.rowCount() - 1)
        else:
            self.upButton.setEnabled(False)
            self.downButton.setEnabled(False)

#         if self.selectedFields.hasIndex(1,0):
#             # there are at least two rows
#             self.upButton.setEnabled(True)
#             self.downButton.setEnabled(True)
#         else:
#             self.upButton.setEnabled(False)
#             self.downButton.setEnabled(False)

    ########################################################
    ## SLOTS
    ########################################################
    def slotAddButtonClicked(self):
        # take current selection from availableFieldsDisplay 
        theIndex = self.availableFieldsDisplay.currentIndex()
        assert theIndex.isValid()
        theItem = self.availableFields.itemFromIndex(theIndex)
        theText = theItem.text()

        # remove that from availableFields
        self.availableFields.removeRow(theIndex.row())
        if self.availableFields.rowCount() > theIndex.row():
            self.availableFieldsDisplay.setCurrentIndex(self.availableFields.indexFromItem(self.availableFields.item(theIndex.row())))
        elif self.availableFields.rowCount() > theIndex.row() - 1:
            # at the end
            self.availableFieldsDisplay.setCurrentIndex(self.availableFields.indexFromItem(self.availableFields.item(theIndex.row() - 1)))
        # otherwise, that's empty

        # add it to selectedFields, before the current selection
        selIndex = self.selectedFieldsDisplay.currentIndex()
        if selIndex.isValid():
           currentSelectedFieldsPosition = selIndex.row()
        else:
           currentSelectedFieldsPosition = 0
        newItem = QtGui.QStandardItem(theText)
        newItem.setEditable(False)
        self.selectedFields.insertRow(currentSelectedFieldsPosition,newItem)

        # make sure we have a selection
        selIndex = self.selectedFieldsDisplay.currentIndex()
        if not selIndex.isValid():
            self.selectedFieldsDisplay.setCurrentIndex(self.selectedFields.indexFromItem(self.selectedFields.item(0)))

        self.updateButtonStatus()
        self.fieldChoiceChanged.emit(self.getCurrentSelectedFields())
    
    def slotRemoveButtonClicked(self):
        # take current selection from selectedFieldsDisplay 
        theIndex = self.selectedFieldsDisplay.currentIndex()
        assert theIndex.isValid()
        theItem = self.selectedFields.itemFromIndex(theIndex)
        theText = theItem.text()

        # remove that from selectedFields
        self.selectedFields.removeRow(theIndex.row())
        if self.selectedFields.rowCount() > theIndex.row():
            self.selectedFieldsDisplay.setCurrentIndex(self.selectedFields.indexFromItem(self.selectedFields.item(theIndex.row())))
        elif self.selectedFields.rowCount() > theIndex.row() - 1:
            # at the end
            self.selectedFieldsDisplay.setCurrentIndex(self.selectedFields.indexFromItem(self.selectedFields.item(theIndex.row() - 1)))
        # otherwise, that's empty

        # add it to availableFields
        currentAvFieldsPosition = 0
        newItem = QtGui.QStandardItem(theText)
        newItem.setEditable(False)
        self.availableFields.insertRow(currentAvFieldsPosition,newItem)

        # make sure we have a selection
        avIndex = self.availableFieldsDisplay.currentIndex()
        if not avIndex.isValid():
            self.availableFieldsDisplay.setCurrentIndex(self.availableFields.indexFromItem(self.availableFields.item(0)))

        self.updateButtonStatus()
        self.fieldChoiceChanged.emit(self.getCurrentSelectedFields())
        pass
    
    def slotUpButtonClicked(self):
        theIndex = self.selectedFieldsDisplay.currentIndex()
        assert theIndex.isValid()
        currentRow = theIndex.row()
        assert currentRow > 0
        otherRow = currentRow - 1

        # swap elements by text
        currentItem = self.selectedFields.item(currentRow)
        otherItem = self.selectedFields.item(otherRow)
        currentText = currentItem.text()
        otherText = otherItem.text()
        currentItem.setText(otherText)
        otherItem.setText(currentText)

        # change selection
        self.selectedFieldsDisplay.setCurrentIndex(self.selectedFields.indexFromItem(self.selectedFields.item(otherRow)))

        # update
        self.updateButtonStatus()
        self.fieldChoiceChanged.emit(self.getCurrentSelectedFields())

    def slotDownButtonClicked(self):
        theIndex = self.selectedFieldsDisplay.currentIndex()
        assert theIndex.isValid()
        currentRow = theIndex.row()
        assert currentRow < self.selectedFields.rowCount() - 1
        otherRow = currentRow + 1

        # swap elements by text
        currentItem = self.selectedFields.item(currentRow)
        otherItem = self.selectedFields.item(otherRow)
        currentText = currentItem.text()
        otherText = otherItem.text()
        currentItem.setText(otherText)
        otherItem.setText(currentText)

        # change selection
        self.selectedFieldsDisplay.setCurrentIndex(self.selectedFields.indexFromItem(self.selectedFields.item(otherRow)))

        # update
        self.updateButtonStatus()
        self.fieldChoiceChanged.emit(self.getCurrentSelectedFields())

    def slotUpdateButtonStatus(self):
        self.updateButtonStatus()


