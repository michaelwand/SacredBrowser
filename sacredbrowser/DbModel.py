from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from PyQt4 import QtCore, QtGui

import re

# Super-simple tree consisting of nodes with extra info. Each node automatically
# assigns itself to its parent.
#
# A leaf node contains the following fields:
# - databaseName: Name of the Mongo database
# - collectionId: "Basic" name of the collection. Sacred uses multiple collections per experiment,
#   names "<name>.runs, <name>.chunks, and <name>.files (the latter are for GridFS). This
#   would be the <name>
# - runCollectionName: Name of the associated collection which contains the experiment data.
#   currently may be "experiments" for older sacred versions, and "<name>.runs" for newer versions. 
# - gridCollectionPrefix: Name of the data collection, according to how GridFS works, this is <name>
#   if this collection is present, and None if not (older sacred versions)
# - text is the displayed text within the tree
#
# Each element knows its row (a QT model requirement),
# this is assured by having an invisible root element for all tree nodes
class TreeNode(object):
    def __init__(self,parent,text,databaseName,collectionId,runCollectionName,gridCollectionPrefix):
        super(TreeNode,self).__init__()
        self.parent = parent
        self.text = text
        if parent is not None: # otherwise, it's the invisible root
            self.row = len(parent.children)
            parent.children.append(self)
        else:
            self.row = -1
        # may be None
        self.databaseName = databaseName
        self.collectionId = collectionId
        self.runCollectionName = runCollectionName
        self.gridCollectionPrefix = gridCollectionPrefix
        self.children = []

    def __del__(self):
#         print('Deleting node with text %s' % self.text)
        pass


# Model for the database tree which is displayed in the left part of the main window.
# The behavior of this class follows the requirements of the QtCore.QAbstractItemModel (weird!).
# Note that this class is tightly coupled with the Sacred database structure.
class DbModel(QtCore.QAbstractItemModel):
    ########################################################
    ## INITIALIZATION AND OVERLOADS
    ########################################################

    # does almost nothing
    def __init__(self,application):
        super(DbModel,self).__init__()
        self.application = application
        self.rootElement = TreeNode(None,'INVALID',None,None,None,None)

    # make a model index
    def index(self,row,column,parent):

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
        assert treeNode.parent is not None
        if treeNode.parent is None:
            pass # TODO FIXME XXX but Qt models *are* messy!
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
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.ToolTipRole:
            return node.text ####if index.column() == 0 else 'fooooo'
        return None

    # the header to be displayed in the widget
    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole and section == 0:
            return 'Database'
        return None


    # this function rebuilds the entire model
    def doReset(self):
        self.beginResetModel()
        # remove all current content by deleting access pointers
        self.rootElement.children = []

        # fill with connection content
        connection = self.application.connection

        for (dbIndex,dbElem) in enumerate(connection.getDatabaseNames()):
            thisDb = connection.getDatabase(dbElem)
            thisDbNode = TreeNode(self.rootElement,dbElem,None,None,None,None)

            collections = [ x for x in connection.getCollectionNames(thisDb) if x != 'system.indexes' ] # remove system DB

            if 'experiments' in collections:
                # old sacred version
                thisChild = TreeNode(thisDbNode,'(default)',dbElem,'experiments','experiments',None)
            else:
                # go through list according to what sacred saves
                allRuns = [ x for x in collections if re.match('.*runs$',x) ]
                for runCollectionName in allRuns:
                    basis = re.match(r'^(.*)\.runs$',runCollectionName).groups()[0]
                    if basis + '.chunks' in collections and  basis + '.files' in collections:
                        gridCollectionPrefix = basis
                    else:
                        print('Info: Collection %s has no attached files!' % runCollectionName)
                        gridCollectionPrefix = None
                    thisChild = TreeNode(thisDbNode,basis,dbElem,basis,runCollectionName,gridCollectionPrefix)

                

        self.endResetModel()


