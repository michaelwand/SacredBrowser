from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from PyQt4 import QtCore, QtGui

# Super-simple tree consisting of nodes, with texts. A leaf node contains a tuple
# collectionInfo = (databaseName,collectionName). Each element knows its
# row, this is assured by having an invisible root element for all tree nodes
class TreeNode(object):
    def __init__(self,parent,text,collectionInfo):
        super(TreeNode,self).__init__()
        self.parent = parent
        self.text = text
        if parent is not None: # otherwise, it's the invisible root
            self.row = len(parent.children)
            parent.children.append(self)
        else:
            self.row = -1
        self.collectionInfo = collectionInfo # may be None
        self.children = []

    def __del__(self):
        print('Deleting node with text %s' % self.text)


# Model for the database tree which is displayed in the left part of the main window.
# The behavior of this class follows the requirements of the QtCore.QAbstractItemModel (weird!)
class DbModel(QtCore.QAbstractItemModel):
    ########################################################
    ## INITIALIZATION AND OVERLOADS
    ########################################################

    # does almost nothing
    def __init__(self,application):
        super(DbModel,self).__init__()
        self.application = application
        self.rootElement = TreeNode(None,'INVALID',None)

    # make a model index
    def index(self,row,column,parent):
#         print('Called index(%d,%d,%s)' % (row,column,parent))

        assert column == 0

        if parent.isValid():
            parentNode = parent.internalPointer()
        else:
            parentNode = self.rootElement

        childNode = parentNode.children[row]
        assert childNode.row == row
        assert childNode.parent is not None
        assert childNode.text != 'INVALID'

        # this is how it must be
        return self.createIndex(row,column,childNode)


    # return a model index corresponding to the parent of the passed model index
    def parent(self,index):
        if not index.isValid():
            return QtCore.QModelIndex()
        treeNode = index.internalPointer()
        # cannot fail
        if treeNode.parent is None:
            print('ARGH')
        return self.createIndex(treeNode.parent.row,0,treeNode.parent)

    def rowCount(self, parent):
        if parent.isValid():
            parentNode = parent.internalPointer()
        else:
            parentNode = self.rootElement
        return len(parentNode.children)

    def columnCount(self, parent):
        return 1

    def data(self, index, role):
        if not index.isValid():
            return None
        node = index.internalPointer()
        if role == QtCore.Qt.DisplayRole:
            return node.text ####if index.column() == 0 else 'fooooo'
        return None

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole and section == 0:
            return 'Database'
        return None



    def doReset(self):
        self.beginResetModel()
        # remove all current content by deleting access pointers
        self.rootElement.children = []

        # fill with connection content
        connection = self.application.connection

        for (dbIndex,dbElem) in enumerate(connection.getDatabaseNames()):
            thisDb = connection.getDatabase(dbElem)
            thisDbNode = TreeNode(self.rootElement,dbElem,None)
            for (clIndex,clElem) in enumerate(connection.getCollectionNames(thisDb)):
                thisChild = TreeNode(thisDbNode,clElem,(dbElem,clElem))

        print('Now DB roots are %s' % str(self.rootElement))
        self.endResetModel()


