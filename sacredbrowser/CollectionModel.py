from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


from PyQt4 import QtCore, QtGui

import Config
import time
import re

import DetailsDialog

import pymongo
import bson

class CollectionModel(QtCore.QAbstractTableModel):
    ########################################################
    ## CONSTANTS
    ########################################################

    # color backgrounds for database entries with different properties
    DuplicateColor = QtGui.QColor(255,255,150)
    FailedColor = QtGui.QColor(255,50,50)
    InterruptedColor = QtGui.QColor(255,150,150)
    RunningColor = QtGui.QColor(200,200,255)

    # note: also used as IDs in the QButtonGroup
    ResultViewRaw = 1
    ResultViewRounded = 2
    ResultViewPercent = 3


    ########################################################
    ## INITIALIZATION
    ########################################################

    # constructor
    def __init__(self,application):
        
        self.application = application

        # this pointer should be set immediately after construction
        self.viewPointer = None

        # This field contains ALL fields (=headers) belonging to the currently displayed collection, as
        # a sorted list
        self.allConfigFields = []

        # The config fields which are currently displayed. This is set by the fieldChoice widget,
        # which calls slotFieldSelectionChanged
        # Note that self.displayedFields() returns self.displayedConfigFields + self.resultFields
        self.displayedConfigFields = []

        # The current result fields (counted)
        self.resultFields = []

        # The last executed query.
        self.lastQuery = None

        # This is the list structure which is currently displayed. Each element is a tuple
        # (modelIndex, dbEntry)
        self.collectionData = []

        # length of result vector - necessary for good display
        self.resultLength = -1
        
        # result view mode 
        self.resultViewMode = CollectionModel.ResultViewRaw

        # allow quick delete (without confirmation)
        self.allowQuickDelete = False

        # might have to go last
        super(CollectionModel,self).__init__()

    ########################################################
    ## OVERLOADS
    ########################################################
    def rowCount(self, parent = None):
        return len(self.collectionData)

    def columnCount(self, parent = None):
        return len(self.displayedFields())

    # Main accessor function to the data underlying this model
    def data(self, index, role):
        if not index.isValid():
            return None
        entry = self.collectionData[index.row()][1]
        field = self.displayedFields()[index.column()]
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.ToolTipRole:
            if re.match(r'^Result [0-9]+$',field):
                number = int(re.match(r'^Result ([0-9]+)$',field).groups()[0]) - 1 # counting!!!
                try:
                    resValue = float(entry['result'][number])
                    if self.resultViewMode == CollectionModel.ResultViewRaw:
                        res = unicode(resValue)
                    elif self.resultViewMode == CollectionModel.ResultViewRounded:
                        resValue = round(resValue,2)
                        res = unicode(resValue)
                    elif self.resultViewMode == CollectionModel.ResultViewPercent:
                        resValue = round(resValue * 100,2)
                        res = unicode(resValue) + '%'
                    else:
                        raise Exception('Wrong result view mode!')
                except (KeyError,IndexError):
                    res = '---'
            else:
                try:
                    res = entry['config'][field]
                except KeyError:
                    res = 'XXX'
            return res
        elif role == QtCore.Qt.BackgroundColorRole:
            if entry['DuplicateMarker']:
                return QtGui.QBrush(self.DuplicateColor)
            elif entry['status'] == 'FAILED':
                return QtGui.QBrush(self.FailedColor)
            elif entry['status'] == 'INTERRUPTED':
                return QtGui.QBrush(self.InterruptedColor)
            elif entry['status'] == 'RUNNING':
                return QtGui.QBrush(self.RunningColor)
            else:
                return None
        else:
            return None

    # column (field) headers
    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return self.displayedFields()[section]
            elif orientation == QtCore.Qt.Vertical:
                return str(section)
        else:
            return None


    ########################################################
    ## MAIN PART
    ########################################################

    # return the associated view
    def getAssociatedView(self):
        return self.application.mainWin.collectionView

    # return the list of displayed fields
    def displayedFields(self):
        return self.displayedConfigFields + self.resultFields

    # retrieves the column widths from the associated view
    def getColumnWidths(self):
        columnWidths = dict()
        for i in range(self.columnCount()):
            thisField = self.headerData(i,QtCore.Qt.Horizontal,QtCore.Qt.DisplayRole)
            columnWidths[thisField] = self.getAssociatedView().columnWidth(i) 
        assert set(columnWidths.keys()) == set(self.displayedFields())
        return columnWidths

    # sets the column widths, pass in a dict indexed by field name
    def setColumnWidths(self,cwDict):
        for i in range(self.columnCount()):
            thisField = self.headerData(i,QtCore.Qt.Horizontal,QtCore.Qt.DisplayRole)
            thisWidth = cwDict.get(thisField,self.getAssociatedView().DefaultColumnWidth)
            self.getAssociatedView().setColumnWidth(i,max(self.getAssociatedView().MinimumColumnWidth,thisWidth))

    # Called when the column size changes. Saves the change to the configuration
    def slotSectionResized(self,column,oldWidth,newWidth):
        self.application.settings.setValue('Collections' + '/' + self.application.collectionSettingsName + '/' + 'columnWidths',self.getColumnWidths())

    # Called to reset the column widths
    def slotResetColWidth(self):
        self.getAssociatedView().resizeColumnsToContents()
#     # saves the column widths to settings, called when the collection changes
#     def saveColumnWidths(self):
#         # also column widths
#         self.application.settings.setValue('Collections' + '/' + self.application.collectionSettingsName + '/' + 'columnWidths',self.getColumnWidths())

    # Resets all content of this view, emits suitable signals to the fieldView and the sort dialog.
    def resetCollection(self):
        # get current collection from application, create a query, read all configs to determine 
        # the possible headers

        # read stuff from settings (check later whether that's valid)

        # read displayed fields from settings
        lastDispFields = self.application.settings.value('Collections' + '/' + self.application.collectionSettingsName + '/' + 'displayedConfigFields')
        # retrieve sort order
        lastSortOrder = self.application.settings.value('Collections' + '/' + self.application.collectionSettingsName + '/' + 'sortOrder')
        # retrieve column widths
        lcwTemp = self.application.settings.value('Collections' + '/' + self.application.collectionSettingsName + '/' + 'columnWidths')

        # retrieve view mode
        lastViewMode = self.application.settings.value('Collections' + '/' + self.application.collectionSettingsName + '/' + 'resultViewMode')

        # start here
        self.layoutAboutToBeChanged.emit()

        # first make headers
        entries = list(self.application.currentCollection.find({}))
        allConfigFields = set()
        # add config entries to displayed headers, and determine the length of "result"
        self.resultLength = -1
        for entry in entries:
            for option in entry['config']:
                allConfigFields.add(unicode(option))
            if 'result' in entry:
                if entry is None:
                    continue # forget it
                elif type(entry['result']) in [ tuple,list ]:
                    thisResultLength = len(entry['result'])
                else: # hm
                    thisResultLength = 1
                if thisResultLength > self.resultLength:
                    self.resultLength = thisResultLength


        self.allConfigFields = list(allConfigFields) 
        self.resultFields = [ 'Result %d' % m for m in range(1,self.resultLength + 1) ]

        # set displayed fields
        if lastDispFields and lastDispFields.isValid():
            # QVariant bug. Cannot save empty list, save 0 instead
            if lastDispFields.toInt()[1]:
                assert lastDispFields.toInt()[0] == 0
                self.displayedConfigFields = []
            else:
                # filter to make sure the fields actually still exist
                self.displayedConfigFields = [str(x.toString()) for x in lastDispFields.toList() if str(x.toString()) in self.allConfigFields]

        else:
            self.displayedConfigFields = list(allConfigFields)
            self.setColumnWidths({}) # set to default

        # query with empty dict - show everything. This fills self.collectionData
        self.makeQuery({}) 

        # tell this the fieldChoice widget - note that slotFieldSelectionChanged is already
        # connected, from the Application class
        # note that the set of displayed fields is ALWAYS augmented by the RESULT field
        self.application.mainWin.fieldChoice.reset(self.allConfigFields,self.displayedConfigFields)
        # the sort dialog is reset by fieldChoiceChanged

        self.application.mainWin.filterChoice.reset()
        
        if lastSortOrder and lastSortOrder.isValid():
            # filter to make sure the fields actually still exist
            lastSortOrderFields = [str(x.toString()) for x in lastSortOrder.toList() if str(x.toString()) in self.displayedFields()]
            self.application.sortDialog.setSortOrder(lastSortOrderFields)
            
        # set column widths
        if lcwTemp and lcwTemp.isValid():
            lcwTemp = lcwTemp.toPyObject()
            # require string keys
            lastColumnWidths = { str(x): lcwTemp[x] for x in lcwTemp.keys() }
            self.setColumnWidths(lastColumnWidths)

        # set view mode
        if lastViewMode and lastViewMode.isValid():
            lastViewModeValue = lastViewMode.toInt()[0]
        else:
            lastViewModeValue = CollectionModel.ResultViewRaw

        # update button group
        if lastViewModeValue == CollectionModel.ResultViewRaw:
            self.application.mainWin.resultViewRaw.setChecked(True)
        elif lastViewModeValue == CollectionModel.ResultViewRounded:
            self.application.mainWin.resultViewRounded.setChecked(True)
        elif lastViewModeValue == CollectionModel.ResultViewPercent:
            self.application.mainWin.resultViewPercent.setChecked(True)

        self.slotResultViewChanged(lastViewModeValue)

        self.layoutChanged.emit()

    # Computes the average of the currently visible data, EXCLUDING duplicates and data points without result.
    # Returns a tuple (or None if no data is visible), raises an exception if something is wrong.
    def getCurrentAverage(self):
        if len(self.collectionData) == 0:
            return None
        
        total = 0
        sums = None
        for tup in self.collectionData:
            entry = tup[1]
            if entry['DuplicateMarker'] == False and 'result' in entry.keys():
                # use this
                total += 1
                if sums is None:
                    sums = list(entry['result'])
                else:
                    if len(entry['result']) != len(sums):
                        raise Exception('Results are not consistent')
                    for i in range(len(sums)):
                        sums[i] += entry['result'][i]
        for i in range(len(sums)):
            sums[i] /= total
        return tuple(sums)


    # Make a new query and fill collectionData
    def makeQuery(self,query=None,guard=True):
        # if query is None, the last query is used
        # guard causes the layout signals to be sent
        if query is not None:
            self.lastQuery = query
        else:
            query = self.lastQuery

        if query is None:
            print('Warning: Trying to do query without defiing a query')
            return

        entries=list(self.application.currentCollection.find(query))
        # TODO sort
        if guard:
            self.layoutAboutToBeChanged.emit()
        self.collectionData = []

        # search for duplicates
        coveredCompareKeys = []
        duplicateCounter = 0
        resultlessCounter = 0
        for (pos,entry) in enumerate(entries):
            # check if dup
            compKey = Config.compareFunc(entry)
            if compKey in coveredCompareKeys:
                entry['DuplicateMarker'] = True
                duplicateCounter += 1
            else:
                entry['DuplicateMarker'] = False
            coveredCompareKeys.append(compKey)

            # check for result
            if 'result' not in entry.keys():
                resultlessCounter += 1
            else:
                if type(entry['result']) not in [ tuple,list ]:
                    entry['result'] = (entry['result'],)

            index = self.createIndex(pos, 0, entry)
            tup = (index,entry)
            self.collectionData += [ tup ]
        if guard:
            self.layoutChanged.emit()

        self.application.showStatusMessage('Loaded %d entries, found %d possible duplicates, %d without result' % (len(entries),duplicateCounter,resultlessCounter))
        self.displayAverage()

    # called to update the display of column averages
    def displayAverage(self):
        try:
            average = self.getCurrentAverage()
            if average is None:
                self.application.mainWin.average.setText('No data visible')
            else:
                # avoid oversized window
                if len(average) > 10:
                    average = average[0:10]
                    avSuffix = '...'
                else:
                    avSuffix = ''
                # is a list
                if self.resultViewMode == CollectionModel.ResultViewRaw:
#                     avTemp = [str(av) for av in average ]
                    avTemp = ['%.2f' % (av) for av in average ]
                elif self.resultViewMode == CollectionModel.ResultViewRounded:
                    avTemp = ['%.2f' % (av) for av in average ]
                elif self.resultViewMode == CollectionModel.ResultViewPercent:
                    avTemp = ['%.2f%%' % (av * 100) for av in average ]
                else:
                    raise Exception('Wrong result view mode!')
                average = ','.join(avTemp)
                self.application.mainWin.average.setText('Averages (excluding duplicates): %s %s' % (str(average),avSuffix))
        except Exception as e:
            self.application.mainWin.average.setText('Cannot compute averages: %s' % str(e))


    ########################################################
    ## SLOTS (called from helper widgets etc)
    ########################################################

    # called when the set of fields to be displayed has been changed
    def slotFieldSelectionChanged(self,newFieldList):
        newFieldList = [unicode(x) for x in newFieldList]
        for f in newFieldList:
            assert f in self.allConfigFields

        cwDict = self.getColumnWidths()

        # now change layout
        self.layoutAboutToBeChanged.emit()
        self.displayedConfigFields = newFieldList
        self.resultFields = [ 'Result %d' % m for m in range(1,self.resultLength + 1) ]

        self.setColumnWidths(cwDict)

        self.layoutChanged.emit()
        self.application.sortDialog.reset(self.displayedFields())

        # write config
        if len(self.displayedConfigFields) > 0:
            self.application.settings.setValue('Collections' + '/' + self.application.collectionSettingsName + '/' + 'displayedConfigFields',self.displayedConfigFields)
        else: # QVariant bug: cannot store empty list, save 0 instead
            self.application.settings.setValue('Collections' + '/' + self.application.collectionSettingsName + '/' + 'displayedConfigFields',0)

    # called when the sort order of entries must be changed due to a command from the sort dialog
    def slotSortOrderChanged(self):
        allEntries = [ e[1] for e in self.collectionData ]
        sortOrder = self.application.sortDialog.currentSortOrder

        # too complicated to be a lambda
        def sortKey(entry):
            key = []
            for field in sortOrder:
                match = re.match(r'^Result ([0-9]+)$',field)
                if not match:
                    key.append(entry['config'].get(field))
                else:
                    try:
                        key.append(entry['result'][int(match.groups()[0]) - 1]) # count from 0
                    except IndexError:
                        key.append(None)
                    except KeyError:
                        key.append(None)
            return key

        allEntries.sort(key=sortKey)

        self.layoutAboutToBeChanged.emit()
        self.collectionData = []

        for (pos,entry) in enumerate(allEntries):
            index = self.createIndex(pos, 0, entry)
            tup = (index,entry)
            self.collectionData += [ tup ]

        self.layoutChanged.emit()

        # save to settings
        self.application.settings.setValue('Collections' + '/' + self.application.collectionSettingsName + '/' + 'sortOrder',sortOrder)

    # called when a new filter has been input to the FilterChoice widget, or when a new collection
    # was loaded
    def slotDoNewSearch(self,queryDict = None):
        # Fill self.collectionData. Layout signals are emitted automatically
        self.makeQuery(queryDict) 

        # resort
        self.slotSortOrderChanged()

    # called when the 'Results in %' checkbox was toggled
    def slotResultViewChanged(self,modeId):
        print('Call to slotResultViewChanged(%d)' % modeId)
        # change the view
        self.layoutAboutToBeChanged.emit()
        self.resultViewMode = modeId
        self.layoutChanged.emit()

        # save that to settings
        if self.application.currentDatabase is not None and self.application.currentCollection is not None:
            self.application.settings.setValue('Collections' + '/' + self.application.collectionSettingsName + '/' + 'resultViewMode',modeId)

        # change average
        self.displayAverage()

    # called when the 'allow delete without confirmation' checkbox was toggled
    def slotAllowQuickDeleteToggled(self,state):
        if state > 0:
            self.allowQuickDelete = True
        else:
            self.allowQuickDelete = False

        # save to settings
        self.application.settings.setValue('Global/quickDeleteChecked',self.allowQuickDelete)

    # copies the content of the selection to the clipboard
    def slotCopyToClipboard(self):
        indexes = self.getAssociatedView().selectedIndexes()

        if len(indexes) == 0:
            return

        # sort: first row, then column
        sortKey = lambda ind: (ind.row(),ind.column())
        indexes.sort(key=sortKey)
        
        # minimum column for proper alignment
        minCol = min([ind.column() for ind in indexes])

        # now make CSV. Count rows for status message.
        curRow = indexes[0].row()
        curCol = minCol
        textResult = ''
        allRows = set()
        for ind in indexes:
            thisRow = ind.row()
            thisCol = ind.column()
            thisData = str(self.data(ind,QtCore.Qt.DisplayRole))
            assert thisRow >= curRow
            for rowX in range(curRow,thisRow):
                textResult += '\n'
                curCol = minCol # reset at new line
            curRow = thisRow
            for colX in range(curCol,thisCol):
                textResult += ','
            curCol = thisCol

            textResult += thisData
            allRows.add(thisRow)

        # copy that
        self.application.clipboard().setText(textResult)
        self.application.showStatusMessage('Copied %d cells from %d entries.' % (len(indexes),len(allRows)))

    # called when the "full entry" dialog is to be shown
    def slotFullEntry(self):
        indexes = self.getAssociatedView().selectedIndexes()
        rows = list(set([ind.row() for ind in indexes]))
        
        if len(rows) != 1:
            QtGui.QMessageBox.warning(None,'Error displaying entry details','For displaying full details, please choose exactly one row')
            return
            
        # sort: first row, then column
        thisEntry = self.collectionData[rows[0]][1]
        dlg = DetailsDialog.DetailsDialog(thisEntry)
        dlg.exec_()

    # called to delete the selected ROWS
    def slotDeleteSelection(self):
        # get entries - we care only for the rows
        indexes = self.getAssociatedView().selectedIndexes()

        if len(indexes) == 0:
            return

        rows = set([ i.row() for i in indexes ])

        # ask
        if not self.allowQuickDelete:
            reply = QtGui.QMessageBox.warning(None,'Really proceed?','Delete %d lines?' % len(rows),QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.No:
                return

        # delete
        entries = [self.collectionData[i][1] for i in rows]
        for entry in entries:
            thisId = entry['_id']
            print('WILL DELETE ENTRY %s with id %s' % (entry['config'],thisId))
            self.application.currentCollection.remove({'_id': bson.objectid.ObjectId(thisId)})
    
        # remove selection
        self.getAssociatedView().selectionModel().clear()

        # update
        self.slotDoNewSearch()


