
from PyQt5 import QtCore, QtGui, QtWidgets

# The database selection tree displayed as the left part of the main window.
class DbTree(QtWidgets.QTreeView):
    def __init__(self,application):
        super(DbTree,self).__init__()
        self.application = application
        self.setSizePolicy (QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
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







