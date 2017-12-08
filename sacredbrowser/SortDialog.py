from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


from PyQt4 import QtCore, QtGui

# The Sort dialog, with a grid of sorting buttons
class SortDialog(QtGui.QDialog):
    # Constant giving the number of search keys
    MaxSortKeyCount = 6

    ########################################################
    ## SIGNALS
    ########################################################
        
    closeCalled = QtCore.pyqtSignal()

    ########################################################
    ## MAIN PART
    ########################################################
        
    # Constructor
    def __init__(self,studyController):
        super(SortDialog,self).__init__()
        
        # the model is the only place where the sort order is saved
        self.studyController = studyController

        # main layout, refilled whenever something changes
        self.mainLayout = QtGui.QGridLayout()
        self.setLayout(self.mainLayout)

#         # the current sort order, as a list of field names
#         # the list is automatically shortened to a maximum of MaxSortKeyCount entries
#         self.getCurrentSortOrder() = []

        # container for the search widgets. each lines consists of a field label and the search keys
        self.fieldLines = []

        # stay-on-top button
        self.stayOnTopButton = QtGui.QPushButton("Stucky :-)")
        self.stayOnTopButton.setCheckable(True)
        self.stayOnTopButton.setChecked(False)
        self.stayOnTopButton.toggled.connect(self.slotStayOnTopToggled)
        self.mainLayout.addWidget(self.stayOnTopButton,0,0,QtCore.Qt.AlignBottom)

        self.staysOnTop = False

        # close button
        self.closeButton = QtGui.QPushButton("Close")
        self.closeButton.clicked.connect(self.slotCloseButtonClicked)

        self.mainLayout.addWidget(self.closeButton,1,0,QtCore.Qt.AlignBottom)

        # save window flags
        self.oldWindowFlags = self.windowFlags()

    def getCurrentSortOrder(self):
        return self.studyController.getCurrentSortOrder()

    def getFieldList(self):
        return self.studyController.getDisplayedFields()

    # reimplemented to prevent the dialog from being closed
    def closeEvent(self,event):
        self.slotCloseButtonClicked()
        event.ignore()

    # slot for the "stay on top" button
    def slotStayOnTopToggled(self,on):
        if on:
            self.staysOnTop = True
            self.oldWindowFlags = self.windowFlags()
            self.setWindowFlags(self.oldWindowFlags | QtCore.Qt.WindowStaysOnTopHint)
        else:
            self.staysOnTop = False
            self.setWindowFlags(self.oldWindowFlags)

        # re-show - why?
        self.show()

    # Rebuild the entire GUI and internal data, taking informaion from the studyModel
    def rebuild(self):

        # delete existing widgets, except the close button
        for fl in self.fieldLines:
            for widget in fl:
                self.mainLayout.removeWidget(widget)
                widget.deleteLater()

        self.fieldLines = []

        self.mainLayout.removeWidget(self.stayOnTopButton)
        self.mainLayout.removeWidget(self.closeButton)

        # make GUI
        currentFieldCount = len(self.getCurrentSortOrder())
        for pos in range(len(self.getFieldList())):
            thisLabel = QtGui.QLabel(self.getFieldList()[pos])
            theseButtons = [ SortButton(str(keypos + 1),pos,keypos) for keypos in range(currentFieldCount) ]

            # connect
            for keypos in range(currentFieldCount):
                theseButtons[keypos].sortClicked.connect(self.slotSortButtonClicked)

            self.mainLayout.addWidget(thisLabel,pos,0)
            for keypos in range(currentFieldCount):
                self.mainLayout.addWidget(theseButtons[keypos],pos,keypos + 1)

            self.fieldLines.append([ thisLabel ] + theseButtons)
        self.mainLayout.addWidget(self.stayOnTopButton,len(self.getFieldList()),0,1,currentFieldCount + 1,QtCore.Qt.AlignBottom)
        self.mainLayout.addWidget(self.closeButton,len(self.getFieldList()) + 1,0,1,currentFieldCount + 1,QtCore.Qt.AlignBottom)

        self.updateButtons()


    # make the button checked status reflect the getCurrentSortOrder()
    def updateButtons(self):
        currentFieldCount = len(self.getCurrentSortOrder())
        for row in range(len(self.getFieldList())):
            for col in range(currentFieldCount):
                thisField = self.getFieldList()[row]
                self.fieldLines[row][col + 1].setChecked(self.getCurrentSortOrder()[col] == thisField)

    ########################################################
    ## SLOTS
    ########################################################

    # slot for ANY of the numbered sort buttons
    def slotSortButtonClicked(self,row,col):
        # col is 0 .. MaxSortKeyCount - 1, thisField is the field whose sorting is to be changed
        changedField = self.getFieldList()[row]
        newSortOrder = self.getCurrentSortOrder()

        # three and a half cases

        try:
            changedFieldPos = newSortOrder.index(changedField)

            if changedFieldPos < col:
                # move back in list
                newSortOrder.insert(col + 1,changedField)
                del newSortOrder[changedFieldPos] 
            elif changedFieldPos > col:
                # move forward
                del newSortOrder[changedFieldPos]
                newSortOrder.insert(col,changedField)
            else:
                # do nothing
                pass
        except ValueError:
            # was not in list
            newSortOrder.insert(col,changedField)
            del newSortOrder[-1]

        self.studyController.sortOrderChanged(newSortOrder)
        self.updateButtons()

    # slot for close button - just hides the dialog
    def slotCloseButtonClicked(self):
        self.setVisible(False)
        self.closeCalled.emit()

        
# helper class: a button with position information, so that the different
# numbered sort buttons may be distinguished
class SortButton(QtGui.QPushButton):

    sortClicked = QtCore.pyqtSignal(int,int)

    def __init__(self,text,row,col,parent = None):
        super(SortButton,self).__init__(text,parent)
        self.row = row
        self.col = col
        self.setCheckable(True)
        # autoconnect
        self.clicked.connect(self.slotClicked)

    def slotClicked(self):
        self.sortClicked.emit(self.row,self.col)

