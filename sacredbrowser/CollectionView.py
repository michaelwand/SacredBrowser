from __future__ import division
from __future__ import print_function

from PyQt4 import QtCore, QtGui

class CollectionView(QtGui.QTableView):
    
    ########################################################
    ## DEFAULT VIEW PROPERTIES
    ########################################################

    # Height of rows (try and see)
    RowHeight = 18

    # default column width
    DefaultColumnWidth = 100

    # default minimal column width (used when reading from settings)
    MinimumColumnWidth = 10

    ########################################################
    ## INITIALIZATION
    ########################################################

    def __init__(self,application):
        super(CollectionView,self).__init__()
        self.application = application

        self.setSizePolicy (QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Expanding)
        self.setModel(application.collectionModel)

        vh = self.verticalHeader()
        vh.setResizeMode(QtGui.QHeaderView.Fixed)
        vh.setDefaultSectionSize(self.RowHeight)

#         self.horizontalHeader().sectionResized.connect(self.slotSectionResized)

    # from http://stackoverflow.com/questions/9775323/copying-a-rtf-table-into-the-clipboard-via-qt-or-writing-a-qtextdocument-int

    ########################################################
    ## DISPLAY STUFF
    ########################################################



    ########################################################
    ## SLOTS AND OVERLOADS
    ########################################################

    # QT overload for key events
    def keyPressEvent(self,event):
        if event.matches(QtGui.QKeySequence.Copy):
            self.model().slotCopyToClipboard()
            event.accept()
            return
        elif event.key() == QtCore.Qt.Key_Delete:
            self.model().slotDeleteSelection()
        elif event.key() == QtCore.Qt.Key_Enter:
            self.model().slotFullEntry()
        else:
            event.ignore()
            super(CollectionView,self).keyPressEvent(event)

    # QT overload for mouse double click (calls details dialog)
    def mouseDoubleClickEvent(self, event):
        self.model().slotFullEntry()

