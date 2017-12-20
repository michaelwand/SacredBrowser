from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# TODO READ http://stackoverflow.com/questions/27113262/making-changes-to-a-qtextedit-without-adding-an-undo-command-to-the-undo-stack
import re 

from PyQt4 import QtCore, QtGui

class FilterChoice(QtGui.QWidget):
    ########################################################
    ## SIGNALS
    ########################################################
      
    doNewSearch = QtCore.pyqtSignal(dict, name='doNewSearch')

    ########################################################
    ## MAIN PART
    ########################################################
      
    DocText = \
'''Instructions: Enter several lines with conditions. The basic form is 
ConfigParam : value, where the value is automatically converted to int, float, string,
or certain Python types (currently bool or None).
Alternative ("or") conditions can be written in list style:
ConfigParam: [ val1, val2, etc ]
Regular expressions can be enclosed in slashes:
ConfigParam: /reg.*exp/
The nonexistence of a field can be given as:
ConfigParam: ---
'''


    def __init__(self,application):
        super(FilterChoice,self).__init__()
        self.application = application
        self.setSizePolicy (QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Expanding)

        # make a label, a text editor, and a button
        self.label = QtGui.QLabel(self.DocText)
        self.label.setWordWrap(True)
        self.editor = QtGui.QTextEdit()
        self.editor.setAcceptRichText(False)
        self.editor.setPlainText('')
        self.searchButton = QtGui.QPushButton('New search')
        self.clearButton = QtGui.QPushButton('Clear')
#         self.clearButton.clicked.connect(self.slotClearButtonClicked)
        self.undoButton = QtGui.QPushButton('Undo')
        self.undoButton.clicked.connect(self.editor.undo)

        buttonSubLayout = QtGui.QHBoxLayout()
        buttonSubLayout.addWidget(self.searchButton)
        buttonSubLayout.addWidget(self.clearButton)
        buttonSubLayout.addWidget(self.undoButton)

        self.layout = QtGui.QVBoxLayout()
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.editor)
        self.layout.addLayout(buttonSubLayout)
        self.setLayout(self.layout)

#     # clears the filter input
#     def reset(self,forceEmpty = False):
#         # try to read last query
# 
# #         self.editor.setPlainText(queryText)
#         cursor = self.editor.textCursor()
#         cursor.beginEditBlock()
#         cursor.select(cursor.Document)
#         cursor.removeSelectedText()
# 
#         if not forceEmpty:
#             if self.application.currentDatabase is not None and self.application.currentRunCollection is not None:
#                  lastQuery = self.application.settings.value('Collections' + '/' + self.application.collectionSettingsName + '/' + 'query')
#                  if lastQuery and lastQuery.isValid():
#                      cursor.insertText(str(lastQuery.toString()))
# 
#         cursor.endEditBlock()
#         self.slotSearchButtonClicked()

    ########################################################
    ## SLOTS
    ########################################################
      
#     def slotSearchButtonClicked(self):
#         try:
#             queryDict = self.validateQuery(self.editor.toPlainText())
#             # save to settings
#             if self.application.currentDatabase is not None and self.application.currentRunCollection is not None:
#                 self.application.settings.setValue('Collections' + '/' + self.application.collectionSettingsName + '/' + 'query',self.editor.toPlainText())
# 
#             self.doNewSearch.emit(queryDict)
#         except FilterChoice.WrongQueryException as e:
#             QtGui.QMessageBox.warning(None,'Cannot parse query',str(e))

#     def slotClearButtonClicked(self):
#         self.reset(True)
