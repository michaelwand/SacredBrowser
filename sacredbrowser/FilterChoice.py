
# TODO READ http://stackoverflow.com/questions/27113262/making-changes-to-a-qtextedit-without-adding-an-undo-command-to-the-undo-stack
import re 

from PyQt5 import QtCore, QtGui, QtWidgets

class FilterChoice(QtWidgets.QWidget):
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
        self.setSizePolicy (QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding)

        # make a label, a text editor, and a button
        self.label = QtWidgets.QLabel(self.DocText)
        self.label.setWordWrap(True)
        self.editor = QtWidgets.QTextEdit()
        self.editor.setAcceptRichText(False)
        self.editor.setPlainText('')
        self.searchButton = QtWidgets.QPushButton('New search')
        self.clearButton = QtWidgets.QPushButton('Clear')
#         self.clearButton.clicked.connect(self.slotClearButtonClicked)
        self.undoButton = QtWidgets.QPushButton('Undo')
        self.undoButton.clicked.connect(self.editor.undo)

        buttonSubLayout = QtWidgets.QHBoxLayout()
        buttonSubLayout.addWidget(self.searchButton)
        buttonSubLayout.addWidget(self.clearButton)
        buttonSubLayout.addWidget(self.undoButton)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.editor)
        self.layout.addLayout(buttonSubLayout)
        self.setLayout(self.layout)

