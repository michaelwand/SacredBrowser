
# TODO READ http://stackoverflow.com/questions/27113262/making-changes-to-a-qtextedit-without-adding-an-undo-command-to-the-undo-stack
import re 

from PyQt5 import QtCore, QtGui, QtWidgets

class FilterChoice(QtWidgets.QWidget):

    new_request = QtCore.pyqtSignal(str,name='new_search_request')
    ############# Main part #############
      
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


    def __init__(self):
        super(FilterChoice,self).__init__()
        self.setSizePolicy (QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding)

        # make a label, a text editor, and a button
        self.label = QtWidgets.QLabel(self.DocText)
        self.label.setWordWrap(True)
        self.editor = QtWidgets.QPlainTextEdit()
#         self.editor.setAcceptRichText(False)
        self.editor.setPlainText('')
        self.search_button = QtWidgets.QPushButton('New search')
        self.clear_button = QtWidgets.QPushButton('Clear')
#         self.clearButton.clicked.connect(self.slotClearButtonClicked)
        self.undo_button = QtWidgets.QPushButton('Undo')
        self.undo_button.clicked.connect(self.editor.undo)

        button_sub_layout = QtWidgets.QHBoxLayout()
        button_sub_layout.addWidget(self.search_button)
        button_sub_layout.addWidget(self.clear_button)
        button_sub_layout.addWidget(self.undo_button)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.editor)
        self.layout.addLayout(button_sub_layout)
        self.setLayout(self.layout)

        self.search_button.clicked.connect(self.slot_search_clicked)

    def slot_search_clicked(self):
        self.new_search_request.emit(self.editor.toPlainText())


