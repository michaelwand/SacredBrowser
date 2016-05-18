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
    sortOrderChanged = QtCore.pyqtSignal()

    ########################################################
    ## MAIN PART
    ########################################################
        
    # Constructor
    def __init__(self):
        super(SortDialog,self).__init__()

        # main layout, refilled whenever something changes
        self.mainLayout = QtGui.QGridLayout()
        self.setLayout(self.mainLayout)

        # list of strings with field names
        # to map from field position to name
        self.fieldList = []

        # the current sort order, as a list of field names
        # the list is automatically shortened to a maximum of MaxSortKeyCount entries
        self.currentSortOrder = []

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

    # rebuild the entire GUI and internal data
    def reset(self,fieldList):
        # let old order survive, if existing
        for fieldX in range(len(self.currentSortOrder) - 1,-1,-1):
            if self.currentSortOrder[fieldX] not in fieldList:
                del self.currentSortOrder[fieldX] # that's why we count backwards

        self.fieldList = fieldList
        if len(self.currentSortOrder) < min(SortDialog.MaxSortKeyCount,len(fieldList)):
            # extend
            for fld in fieldList:
                if fld not in self.currentSortOrder:
                    self.currentSortOrder.append(fld)

        self.currentSortOrder = self.currentSortOrder[0:SortDialog.MaxSortKeyCount] # OK even for shorter lists
#         print('NOW ORDER:: ',self.currentSortOrder)

        # delete existing widgets, except the close button
        for fl in self.fieldLines:
            for widget in fl:
                self.mainLayout.removeWidget(widget)
                widget.deleteLater()

        self.fieldLines = []

        self.mainLayout.removeWidget(self.stayOnTopButton)
        self.mainLayout.removeWidget(self.closeButton)

        # make GUI
        currentFieldCount = len(self.currentSortOrder)
        for pos in range(len(self.fieldList)):
            thisLabel = QtGui.QLabel(self.fieldList[pos])
            theseButtons = [ SortButton(str(keypos + 1),pos,keypos) for keypos in range(currentFieldCount) ]

            # connect
            for keypos in range(currentFieldCount):
                theseButtons[keypos].sortClicked.connect(self.slotSortButtonClicked)

            self.mainLayout.addWidget(thisLabel,pos,0)
            for keypos in range(currentFieldCount):
                self.mainLayout.addWidget(theseButtons[keypos],pos,keypos + 1)

            self.fieldLines.append([ thisLabel ] + theseButtons)
        self.mainLayout.addWidget(self.stayOnTopButton,len(self.fieldList),0,1,currentFieldCount + 1,QtCore.Qt.AlignBottom)
        self.mainLayout.addWidget(self.closeButton,len(self.fieldList) + 1,0,1,currentFieldCount + 1,QtCore.Qt.AlignBottom)

        self.updateButtons()

        self.sortOrderChanged.emit()

    # make the button checked status reflect the currentSortOrder
    def updateButtons(self):
        currentFieldCount = len(self.currentSortOrder)
        for row in range(len(self.fieldList)):
            for col in range(currentFieldCount):
                thisField = self.fieldList[row]
                self.fieldLines[row][col + 1].setChecked(self.currentSortOrder[col] == thisField)

    def setSortOrder(self,fieldList):
        self.currentSortOrder = fieldList
        self.updateButtons()
        self.sortOrderChanged.emit()


    ########################################################
    ## SLOTS
    ########################################################

    # slot for ANY of the numbered sort buttons, passes on the information to the sortOrderChanged 
    # signal and thus to the collection model
    def slotSortButtonClicked(self,row,col):
        # col is 0 .. MaxSortKeyCount - 1, thisField is the field whose sorting is to be changed
        changedField = self.fieldList[row]

        # three and a half cases

        try:
            changedFieldPos = self.currentSortOrder.index(changedField)

            if changedFieldPos < col:
                # move back in list
                self.currentSortOrder.insert(col + 1,changedField)
                del self.currentSortOrder[changedFieldPos] 
            elif changedFieldPos > col:
                # move forward
                del self.currentSortOrder[changedFieldPos]
                self.currentSortOrder.insert(col,changedField)
            else:
                # do nothing
                pass
        except ValueError:
            # was not in list
            self.currentSortOrder.insert(col,changedField)
            del self.currentSortOrder[-1]

        self.updateButtons()
        self.sortOrderChanged.emit()

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

