
# TODO READ http://stackoverflow.com/questions/27113262/making-changes-to-a-qtextedit-without-adding-an-undo-command-to-the-undo-stack
import re 

from PyQt5 import QtCore, QtGui, QtWidgets



class FilterChoice(QtWidgets.QWidget):

    new_query = QtCore.pyqtSignal(str)

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
        super().__init__()
        self.setSizePolicy (QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding)

        # update placeholder to avoid undesired effects
        self._currently_updating_from_model = False

        # widgets
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

        # layouts
        button_sub_layout = QtWidgets.QHBoxLayout()
        button_sub_layout.addWidget(self.search_button)
        button_sub_layout.addWidget(self.clear_button)
        button_sub_layout.addWidget(self.undo_button)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.editor)
        self.layout.addLayout(button_sub_layout)
        self.setLayout(self.layout)

        # connections
        self.editor.textChanged.connect(self._slot_text_changed)
        self.search_button.clicked.connect(self._slot_search_clicked)

    # internal slots
    def _slot_search_clicked(self):
        self.new_query.emit(self.editor.toPlainText())

    def _slot_text_changed(self):
        if self._currently_updating_from_model:
            return
        print('FilterChoice is WEHITE')
        self.editor.setStyleSheet('QPlainTextEdit { background: white; }')

    # external slots
    def slot_filter_changed(self,new_filter_text,new_filter_dict):
        self._currently_updating_from_model = True
        print('FilterChoice is YELLOW with filter',new_filter_text)
        self.editor.setStyleSheet('QPlainTextEdit { background: yellow; }')
        self.editor.setPlainText(new_filter_text)
        self._currently_updating_from_model = False

    def slot_filter_rejected(self):
        print('FilterChoice is RED')
        self.editor.setStyleSheet('QPlainTextEdit { background: red; }')

# TODO slot study changed?



