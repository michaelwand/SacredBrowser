from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# TODO READ http://stackoverflow.com/questions/27113262/making-changes-to-a-qtextedit-without-adding-an-undo-command-to-the-undo-stack
import re 

from PyQt4 import QtCore, QtGui

class FilterChoice(QtGui.QWidget):
    ########################################################
    ## EXCEPTION
    ########################################################
    class WrongQueryException(Exception):
        pass
      
    ########################################################
    ## SIGNALS
    ########################################################
      
    doNewSearch = QtCore.pyqtSignal(dict, name='doNewSearch')

    ########################################################
    ## MAIN PART
    ########################################################
      
    DocText = \
'''Instructions: Enter several lines with conditions. The basic form is 
ConfigParam : value. The value is automatically converted to int, float, or string.
An item is displayed if the conditions on all lines are fulfilled,
alternative ("or") conditions can be written in list style:
ConfigParam: [ val1, val2, etc ]
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
        self.searchButton.clicked.connect(self.slotSearchButtonClicked)
        self.clearButton = QtGui.QPushButton('Clear')
        self.clearButton.clicked.connect(self.slotClearButtonClicked)
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

    # This badly hacked parser validate the 'filter' user input, adds some quotes 
    # and convert it into a dict, which is returned so that it can be passed on to PyMongo.collection.find
    # raises a WrongQueryException if something is wrong
    def validateQuery(self,queryText):
        # possibly convert a string to a number
        def possiblyConvert(x):
            try:
                cnum = int(x)
                return cnum
            except:
                try:
                    cnum = float(x)
                    return cnum
                except:
                    return str(x)

        # This will be the resulting query. It will have a single key ['$and'], joining one sub-dictionary for each line.
        # This is a requirement to make more complicated mongo queries work.
        resultDict = { '$and': [] }
        processedResultFieldNames = []

        # parse input, line by line
        lines = unicode(queryText).split('\n')
        for (lX,line) in enumerate(lines):
            # skip empty lines and comments
            if re.match(r'^\s*$',line) or re.match(r'^\s*#.*$',line):
                continue
            # must contain exactly one ':'
#             colRe = re.compile(':')
#             if len(colRe.findall(line)) != 1:
#                 raise FilterChoice.WrongQueryException('Line %d must contain exactly one colon (:), contains %d' % (lX,len(colRe.findall(line))))
# 
#             boundary = line.find(':')
#             assert boundary >= 0

#             fieldName = line[0:boundary].strip()
#             content = line[boundary + 1:].strip()
            # basic parsing - field: content
            try:
                (fieldName,content) = line.split(':')
            except ValueError:
                raise FilterChoice.WrongQueryException('Line %d must contain exactly one colon (:), contains %d' % (lX,line.count(':')))

            fieldName = fieldName.strip()
            content = content.strip()
            
            # interpret
            fieldName = str('config.' + fieldName)
            if fieldName in processedResultFieldNames:
                raise FilterChoice.WrongQueryException('Key %s specified twice in line %d' % (fieldName,lX))

            if not (('[' in content) or (']' in content)):
                content = possiblyConvert(content)

                thisResultDict = { fieldName: content }
                resultDict['$and'].append(thisResultDict)
            else:
                # this will be an 'or' query, must have comma-separated conditions enclosed between [], and nothing more
                if not ((content.count('[') == 1) and (content.count(']') == 1)):
                    raise FilterChoice.WrongQueryException('Illegal 'or' command (requires one pair of []) in line %d' % lX)

                startPos = content.find('[')
                endPos = content.find(']')

                if not re.match(r'^\s*$',content[0:startPos]):
                    raise FilterChoice.WrongQueryException('Extra characters before  'or' command in line %d' % lX)
                if not re.match(r'^\s*$',content[endPos:-1]):
                    raise FilterChoice.WrongQueryException('Extra characters after  'or' command in line %d' % lX)
                subContent = content[startPos + 1:endPos]
                subContentData = subContent.split(',')

                if len(subContentData) == 1:
                    # not a real 'or' since just one alternative is given!
                    content = possiblyConvert(subContentData[0])
                    thisResultDict = { fieldName: content }
                    resultDict['$and'].append(thisResultDict)
                else:
                    # make 'or' query
                    thisResultDict = { '$or': [ { fieldName: possiblyConvert(val.strip()) } for val in subContentData ] }
                    resultDict['$and'].append(thisResultDict)

            processedResultFieldNames.append(fieldName)

        return resultDict if len(resultDict['$and']) > 0 else {}

    # clears the filter input
    def reset(self,forceEmpty = False):
        # try to read last query

#         self.editor.setPlainText(queryText)
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()
        cursor.select(cursor.Document)
        cursor.removeSelectedText()

        if not forceEmpty:
            if self.application.currentDatabase is not None and self.application.currentRunCollection is not None:
                 lastQuery = self.application.settings.value('Collections' + '/' + self.application.collectionSettingsName + '/' + 'query')
                 if lastQuery and lastQuery.isValid():
                     cursor.insertText(str(lastQuery.toString()))

        cursor.endEditBlock()
        self.slotSearchButtonClicked()

    ########################################################
    ## SLOTS
    ########################################################
      
    def slotSearchButtonClicked(self):
        try:
            queryDict = self.validateQuery(self.editor.toPlainText())
            # save to settings
            if self.application.currentDatabase is not None and self.application.currentRunCollection is not None:
                self.application.settings.setValue('Collections' + '/' + self.application.collectionSettingsName + '/' + 'query',self.editor.toPlainText())

            self.doNewSearch.emit(queryDict)
        except FilterChoice.WrongQueryException as e:
            QtGui.QMessageBox.warning(None,'Cannot parse query',str(e))

    def slotClearButtonClicked(self):
        self.reset(True)
