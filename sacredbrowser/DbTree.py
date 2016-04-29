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
        self.model = application.dbModel
        self.setModel(self.model)




