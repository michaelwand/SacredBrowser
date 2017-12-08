from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from PyQt4 import QtCore, QtGui

# The database selection tree displayed as the left part of the main window.
class DbTree(QtGui.QTreeView):
    def __init__(self,application):
        super(DbTree,self).__init__()
        self.application = application
        self.setSizePolicy (QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Expanding)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.model = application.dbModel
        self.setModel(self.model)
        self.selectionModel().currentChanged.connect(self.slotCurrentChanged)

    def slotCurrentChanged(self):
        print('DbTree: slotCurrentChanged')
        theIndex = self.currentIndex()
        print('New index:',theIndex)
        if theIndex.isValid():
            print('Valid index: row %d, column %d' % (theIndex.row(),theIndex.column()))
            node = theIndex.internalPointer()
            print('Internal pointer is',node,'and database name is',node.databaseName,'and collection id is',node.collectionId)
        else:
            print('INVALID idnex')







