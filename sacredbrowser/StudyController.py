raise Exception('outdated file, delete')
from PyQt5 import QtCore, QtGui, QtWidgets

import time
import re
import numpy as np
import pymongo
import bson


from . import Config
from . import DetailsDialog

class StudyController():
    ########################################################
    ## CONSTRUCTION
    ########################################################

    # constructor
    def __init__(self,application,studyModel,experimentListModel,experimentListView,filterChoice):
        self.application = application
        self.studyModel = studyModel
        self.experimentListModel = experimentListModel
        self.experimentListView = experimentListView

        self.filterChoice = filterChoice

    ########################################################
    ## ACCESSORS
    ########################################################

    def getDisplayedFields(self):
        return self.studyModel.displayedFields()

    def getCollectionData(self):
        return self.studyModel.getCollectionData()

    def getResultViewMode(self):
        print('OBSOLETE FUNCTION controller - getResultViewMode')
        return self.studyModel.resultViewMode

    def getCurrentSortOrder(self):
        return self.studyModel.currentSortOrder

    def getApplication(self):
        return self.application
      
    ########################################################
    ## SLOTS (called from helper widgets etc)
    ########################################################

    # called when the set of fields to be displayed has been changed
    def slotFieldSelectionChanged(self,newFieldList):
        print('Called slotFieldSelectionChanged')
        if self.studyModel.valid:
            newFieldList = [str(x) for x in newFieldList]
            for f in newFieldList:
                assert f in self.studyModel.allConfigFields
            self.dataAboutToBeChanged()
            self.studyModel.changeDisplayedFieldList(newFieldList)
            self.dataHasBeenChanged()
            self.getApplication().sortDialog.rebuild()
        else:
            newFieldList = []

    # called when a new filter has been input to the FilterChoice widget, or when a new collection
    # was loaded
    def slotDoNewSearchClicked(self):
        try:
            self.dataAboutToBeChanged()
            self.studyModel.performQuery(self.filterChoice.editor.toPlainText())
            self.studyModel.resort()
        except ValueError as e:
            QtGui.QMessageBox.warning(None,'Cannot parse query',str(e))
        finally:
            self.dataHasBeenChanged()

        self.displayAverage()

    def slotClearSearchClicked(self):
        self.filterChoice.editor.setPlainText('')
        try:
            self.dataAboutToBeChanged()
            self.studyModel.performQuery(self.filterChoice.editor.toPlainText())
            self.studyModel.resort()
        except ValueError as e:
            QtGui.QMessageBox.warning(None,'Cannot parse query',str(e))
        finally:
            self.dataHasBeenChanged()
        
        self.displayAverage()

    # called when the 'Results in %' checkbox was toggled
    def slotResultViewChanged(self,modeId):
        # change the view
        self.dataAboutToBeChanged()
        self.studyModel.changeResultViewMode(modeId)
        self.dataHasBeenChanged()

        self.displayAverage()

    # copies the content of the selection to the clipboard
    def slotCopyToClipboard(self):
        indexes = self.experimentListView.selectedIndexes()

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
            thisData = str(self.experimentListModel.data(ind,QtCore.Qt.DisplayRole))
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
        self.getApplication().clipboard().setText(textResult)
        self.getApplication().showStatusMessage('Copied %d cells from %d entries.' % (len(indexes),len(allRows)))

    # called when the "full entry" dialog is to be shown
    def slotFullEntry(self):
        indexes = self.experimentListView.selectedIndexes()
        rows = list(set([ind.row() for ind in indexes]))
        
        if len(rows) != 1:
            QtGui.QMessageBox.warning(None,'Error displaying entry details','For displaying full details, please choose exactly one row')
            return
            
        # sort: first row, then column
        thisEntry = self.getCollectionData()[rows[0]][1]
        dlg = DetailsDialog.DetailsDialog(self.getApplication(),thisEntry,self.getApplication().currentGridFs)
        dlg.exec_()

    # called to delete the selected ROWS
    def slotDeleteSelection(self):
        print('Call to slotDeleteSelection, QD is',self.getApplication().allowQuickDelete)
        # get entries - we care only for the rows
        indexes = self.experimentListView.selectedIndexes()

        if len(indexes) == 0:
            return

        rows = set([ i.row() for i in indexes ])

        # ask
        if not self.getApplication().allowQuickDelete:
            reply = QtGui.QMessageBox.warning(None,'Really proceed?','Delete %d lines?' % len(rows),QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.No:
                return

        # perform actual delete
        self.dataAboutToBeChanged()
        entries = [self.getCollectionData()[i][1] for i in rows]
        for entry in entries:
            thisId = entry['_id']
#             self.getApplication().currentRunCollection.remove({'_id': bson.objectid.ObjectId(thisId)})
            self.getApplication().currentRunCollection.remove({'_id': thisId})
    
        # remove selection
        self.experimentListView.selectionModel().clear()

        # update
        self.slotDoNewSearchClicked()
        self.dataHasBeenChanged()


    # Called when the underlying data is about to change.
    def dataAboutToBeChanged(self):
        self.experimentListModel.dataAboutToBeChanged()

    # Called when the underlying data has been changed.
    def dataHasBeenChanged(self):
        self.experimentListModel.dataHasBeenChanged()

    # Called to reset the column widths
    def slotResetColWidth(self):
        self.experimentListView.resizeColumnsToContents()


    ########################################################
    ## MAIN PART
    ########################################################

    def formatResultValue(self,rawValue):
        if self.studyModel.resultViewMode == self.studyModel.ResultViewRaw:
            res = str(rawValue)
        elif self.studyModel.resultViewMode == self.studyModel.ResultViewRounded:
            resValue = round(rawValue,2)
            res = str(resValue)
        elif self.studyModel.resultViewMode == self.studyModel.ResultViewPercent:
            resValue = round(rawValue * 100,2)
            res = str(resValue) + '%'
        else:
            raise ValueError('Wrong result view mode!')
        return res


    def reset(self):
        # prepare associated views
        self.dataAboutToBeChanged()

        # read data into model
        newModelContainsData = self.studyModel.reset()

        # update associated widgets
        self.getApplication().mainWin.fieldChoice.reset(self.studyModel.allConfigFields,self.studyModel.displayedConfigFields)

        if newModelContainsData:
            self.studyModel.resort()

            self.getApplication().sortDialog.rebuild()

            if self.studyModel.resultViewMode == self.studyModel.ResultViewRaw:
                self.getApplication().mainWin.resultViewRaw.setChecked(True)
            elif self.studyModel.resultViewMode == self.studyModel.ResultViewRounded:
                self.getApplication().mainWin.resultViewRounded.setChecked(True)
            elif self.studyModel.resultViewMode == self.studyModel.ResultViewPercent:
                self.getApplication().mainWin.resultViewPercent.setChecked(True)

            self.filterChoice.editor.setPlainText(self.studyModel.lastQueryText)

            # activate all controls
            self.getApplication().mainWin.enableStudyControls(True)
        else:
            self.filterChoice.editor.setPlainText('')

            # deactivate all controls
            self.getApplication().mainWin.enableStudyControls(False)

        # alert associated views
        self.dataHasBeenChanged()

        self.displayAverage()

    # called when the sort order of entries must be changed due to a command from the sort dialog
    def sortOrderChanged(self,newSortOrder):
        self.dataAboutToBeChanged()
        self.studyModel.changeSortOrder(newSortOrder)
        self.studyModel.resort()
        self.dataHasBeenChanged()

    def selectionChanged(self):
        self.displayAverage()

    # pass on information about column width change to the model
    def columnWidthsChangedFromGui(self,newColumnWidths):
        self.studyModel.columnWidthsChanged(newColumnWidths)

    # get column widths fron the model
    def getColumnWidths(self):
        return self.studyModel.columnWidths

    # TODO move this to model!
    # get average and maximum over results *selected* rows (returns None if no selection found)
    def getAvMaxOverSelectedRows(self):
        indexes = self.experimentListView.selectedIndexes()

        if len(indexes) == 0:
            return None

        
        rows = set([ i.row() for i in indexes ])
        print('rows:',rows)
        return self.getAvMaxOverRows(rows)
      
    def getTotalAvMax(self):
        rows = list(range(len(self.studyModel.getCollectionData())))
        return self.getAvMaxOverRows(rows)   

    def getAvMaxOverRows(self,rows):
        total = 0 
        resultLists = []

        for row in rows:
            entry = self.getCollectionData()[row][1]
            if 'result' in entry.keys():
                if len(resultLists) > 0 and len(resultLists[0]) != len(entry['result']):
                    raise Exception('Length of result lists are not consistent')

                resultLists.append(entry['result']) 

        if len(resultLists) == 0:
            raise Exception('No rows selected')

        avg = np.mean(resultLists,axis=0)
        mx = np.max(resultLists,axis=0)
        return (avg,mx)

    # called to update the display of column averages: over selected rows if there is a selection, 
    # global average otherwise
    def displayAverage(self):
        try:
            res = self.getAvMaxOverSelectedRows()
            isOverSelected = (res is not None)
            if res is None:
                res = self.getTotalAvMax()
                assert res is not None
                
            averages,maxima = res
            assert averages.ndim == 1
            assert maxima.shape == averages.shape
            averages = averages.tolist()
            maxima = maxima.tolist()

            # avoid oversized window
            if len(averages) > 10:
                averages = averages[0:10]
                maxima = maxima[0:10]
                dispSuffix = '...'
            else:
                dispSuffix = ''
            
            formattedAverages = [self.formatResultValue(x) for x in averages]
            formattedMaxima = [self.formatResultValue(x) for x in maxima]
            averageText = ','.join(formattedAverages)
            maximaText = ','.join(formattedMaxima)

            if isOverSelected:
                self.getApplication().mainWin.average.setText('Selection: Avg %s %s; Max %s %s' % (averageText,dispSuffix,maximaText,dispSuffix))
            else:
                self.getApplication().mainWin.average.setText('Total: Avg %s %s; Max %s %s' % (averageText,dispSuffix,maximaText,dispSuffix))
        except Exception as e:
            self.getApplication().mainWin.average.setText('Cannot compute averages: %s' % str(e))


