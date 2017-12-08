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

class StudyModel(object):
    ########################################################
    ## CONSTANTS
    ########################################################

    # display modes for results
    # note: also used as IDs in the QButtonGroup
    ResultViewRaw = 1
    ResultViewRounded = 2
    ResultViewPercent = 3

    # default column width
    DefaultColumnWidth = 100

    # default minimal column width (used when reading from settings)
    MinimumColumnWidth = 10


    ########################################################
    ## CONSTRUCTION
    ########################################################

    def __init__(self,experimentListModel):
        super(StudyModel,self).__init__()
        self.experimentListModel = experimentListModel
        self.studyController = None
        self.initEmpty()

        self.valid = False

    # initialize an empty model (also used when the user has no collection selected)
    def initEmpty(self):
        # This field contains ALL fields (=headers) belonging to the currently displayed collection, as
        # a sorted list
        self.allConfigFields = []

        # The config fields which are currently displayed. This is set by the fieldChoice widget,
        # which calls slotFieldSelectionChanged
        # Note that self.displayedFields() returns self.displayedConfigFields + self.resultFields
        self.displayedConfigFields = []

        # The current result fields (counted)
        self.resultFields = []

        # column widths for the (single) view
        self.columnWidths = {}

        # The last executed query.
        self.lastQueryText = None

        # This is the list structure which is currently displayed. Each element is a tuple
        # (modelIndex, dbEntry)
        self.collectionData = []

        # length of result vector - necessary for good display
        self.resultLength = -1
        
        # result view mode 
        self.resultViewMode = self.ResultViewRaw

        # current sort order
        self.currentSortOrder = []

    ########################################################
    ## MAIN PART
    ########################################################

    # obtain the application object
    def getApplication(self):
        return self.studyController.application

    # return the list of displayed fields
    def displayedFields(self):
        return self.displayedConfigFields + self.resultFields
    
    # returns the "collection data" (FIXME TODO name) to be displayed
    def getCollectionData(self):
        return self.collectionData

    # Resets all content of this view, emits suitable signals to the fieldView and the sort dialog.
    # TODO doku
    def reset(self):
        # get current collection from application, create a query, read all configs to determine the possible headers
        # empty the collection view (and related views) if no collection is chosen
        if self.getApplication().currentRunCollection is None:
            assert self.getApplication().currentRunCollectionName is None

            self.studyController.dataAboutToBeChanged()
            self.initEmpty()
            self.studyController.dataHasBeenChanged()

            self.valid = False
        else:
            # retrieve settings for this collection 
            lastDispFields = self.getApplication().settings.value('Collections' + '/' + self.getApplication().collectionSettingsName + '/' + 'displayedConfigFields')
            lastSortOrder = self.getApplication().settings.value('Collections' + '/' + self.getApplication().collectionSettingsName + '/' + 'sortOrder')
            lastViewMode = self.getApplication().settings.value('Collections' + '/' + self.getApplication().collectionSettingsName + '/' + 'resultViewMode')
            lastQueryText = self.getApplication().settings.value('Collections' + '/' + self.getApplication().collectionSettingsName + '/' + 'lastQueryText')
            lastColumnWidths = self.getApplication().settings.value('Collections' + '/' + self.getApplication().collectionSettingsName + '/' + 'columnWidths')

            # start updating the layout
            self.studyController.dataAboutToBeChanged()

            # first make headers
            self.allConfigFields,self.resultLength = self.getHeaderInfo()
            self.allConfigFields = list(self.allConfigFields) 

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
                self.displayedConfigFields = list(self.allConfigFields)

            # query with empty dict - show everything. This fills self.collectionData
            if lastQueryText and lastQueryText.isValid():
                self.performQuery(lastQueryText.toString(),guard=False) 
            else:
                self.performQuery("",guard=False)
                
            # set view mode
            if lastViewMode and lastViewMode.isValid():
                self.resultViewMode = lastViewMode.toInt()[0]
            else:
                self.resultViewMode = self.ResultViewRaw

            # set sort order
            if lastSortOrder and lastSortOrder.isValid():
                self.currentSortOrder = lastSortOrder.toList()
                for pos in range(len(self.currentSortOrder)):
                    try:
                        self.currentSortOrder[pos] = self.currentSortOrder[pos].toString()
                        self.currentSortOrder[pos] = str(self.currentSortOrder[pos])
                    except Exception as e:
                        pass
            else:
                self.currentSortOrder = self.displayedConfigFields

            self.currentSortOrder = self.currentSortOrder[0:6]

            # set column widths
            if lastColumnWidths and lastColumnWidths.isValid():
                try:
                    lastColumnWidths = lastColumnWidths.toPyObject()
                    self.columnWidths = { str(k): v for k,v in lastColumnWidths.iteritems() }
                except Exception as e:
                    print('Error retrieving column widths: %s' % str(e))
            else:
                self.columnWidths = {}
            self.updateColumnWidths()

            # make data change visible
            self.studyController.dataHasBeenChanged()

            self.valid = True
        return self.valid

    # Obtain header info when a new collection is displayed
    def getHeaderInfo(self):
        entries = list(self.getApplication().currentRunCollection.find({}))
        allConfigFields = set()
        # add config entries to displayed headers, and determine the length of "result"
        resultLength = -1
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
                if thisResultLength > resultLength:
                    resultLength = thisResultLength

        return allConfigFields,resultLength


    # This badly hacked parser validate the 'filter' user input, adds some quotes 
    # and convert it into a dict, which is returned so that it can be passed on to PyMongo.collection.find
    # raises a ValueErro if something is wrong
    def validateQuery(self,queryText):

        print('Call to validateQuery, text is ---%s---' % queryText)
        # HELPER FUNCTIONS

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

        # parse an "or" condition, raise an exception if it goes wrong, return result dictionary to append to the
        # mongo query if OK
        def parseOrCondition(fieldName,content):
            # first check if content has the form [ ... ]
#             if not ((content.count('[') == 1) and (content.count(']') == 1)):
            matchOb = re.match(r'^\s*\[([^\[\]]*)\]\s*$',content)
            if matchOb is None:
                raise ValueError('Illegal 'or' command (required format [ ... ]) in line %d' % lX)

            subContent = matchOb.groups()[0]
            subContentData = subContent.split(',')

            if len(subContentData) == 1:
                # not a real 'or' since just one alternative is given!
                singleSubContent = possiblyConvert(subContentData[0])
                resultDict = { fieldName: singleSubContent }
            else:
                # make 'or' query
                resultDict = { '$or': [ { fieldName: possiblyConvert(val.strip()) } for val in subContentData ] }
            
            return resultDict

        # parse a regexp condition, raise an exception if it goes wrong, return result dictionary to append to the
        # mongo query if OK
        def parseRegexp(fieldName,content):
            # first check if content has the form [ ... ]
#             if not ((content.count('[') == 1) and (content.count(']') == 1)):
            matchOb = re.match(r'^\s*/(.*)/\s*$',content)
            if matchOb is None:
                raise ValueError('Illegal regexp (required format / ... /) in line %d' % lX)

            subContent = matchOb.groups()[0]

            resultDict = { fieldName: { '$regex': subContent.strip() } }

            return resultDict

        # MAIN PART: parse input, line by line

        # This will be the resulting query. It will have a single key ['$and'], joining one sub-dictionary for each line.
        # This is a requirement to make more complicated mongo queries work.
        resultDict = { '$and': [] }
        processedResultFieldNames = []
        
        lines = unicode(queryText).split('\n')
        for (lX,line) in enumerate(lines):
            # skip empty lines and comments
            if re.match(r'^\s*$',line) or re.match(r'^\s*#.*$',line):
                continue

            # basic parsing - split field: content
#                 (fieldName,content) = line.split(':')
            colPos = line.find(':')
            if colPos == -1:
                raise ValueError('Line %d must contain at least one colon (:)')
            fieldName = line[0:colPos]
            content = line[colPos+1:]

            fieldName = fieldName.strip()
            content = content.strip()
            
            # interpret context, several cases ('or' condition, regexp, normal text)
            fieldName = str('config.' + fieldName)
            if fieldName in processedResultFieldNames:
                raise ValueError('Key %s specified twice in line %d' % (fieldName,lX))

            if re.match(r'^\s*\[.*\]\s*$',content):
                thisResultDict = parseOrCondition(fieldName,content)
            elif re.match(r'^\s*/.*/\s*$',content):
                thisResultDict = parseRegexp(fieldName,content)
            else:    #####if not (('[' in content) or (']' in content)):
                # simple content
                content = possiblyConvert(content)

                thisResultDict = { fieldName: content }
            resultDict['$and'].append(thisResultDict)

            processedResultFieldNames.append(fieldName)

        return resultDict if len(resultDict['$and']) > 0 else {}

    # Make a new query and fill collectionData
    def performQuery(self,queryText,guard=True):
        # if query is None, the last query is used
        # guard causes the layout signals to be sent
        query = self.validateQuery(queryText)

        # this has worked - go on
        self.lastQueryText = queryText
        self.getApplication().settings.setValue('Collections' + '/' + self.getApplication().collectionSettingsName + '/' + 'lastQueryText',queryText)

        entries=list(self.getApplication().currentRunCollection.find(query))
        # TODO sort
        if guard:
            self.studyController.dataAboutToBeChanged()
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

#             index = self.createIndex(pos, 0, entry)
            index = None # TODO remove
            tup = (index,entry)
            self.collectionData += [ tup ]
        if guard:
            self.studyController.dataHasBeenChanged()

        self.getApplication().showStatusMessage('Loaded %d entries, found %d possible duplicates, %d without result' % (len(entries),duplicateCounter,resultlessCounter))

    # TODO
    def resort(self):
        allEntries = [ e[1] for e in self.collectionData ]
        print('Call to resort, current order is:',self.currentSortOrder)

        # too complicated to be a lambda
        def sortKey(entry):
            key = []
            for field in self.currentSortOrder:
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

        self.studyController.dataAboutToBeChanged()

        self.collectionData = []

        for (pos,entry) in enumerate(allEntries):
#             index = self.createIndex(pos, 0, entry)
            index = None # TODO remove
            tup = (index,entry)
            self.collectionData += [ tup ]

        self.studyController.dataHasBeenChanged()

        # save to settings
        self.getApplication().settings.setValue('Collections' + '/' + self.getApplication().collectionSettingsName + '/' + 'sortOrder',self.currentSortOrder)

    def changeSortOrder(self,newSortOrder):
        self.currentSortOrder = newSortOrder[0:6]

    def changeDisplayedFieldList(self,newDisplayedFields):
        # now change layout
        self.studyController.dataAboutToBeChanged()
        self.displayedConfigFields = newDisplayedFields
        self.updateColumnWidths()
        self.studyController.dataHasBeenChanged()

        # TODO tell sort dialog
        # write config
        if len(self.displayedConfigFields) > 0:
            self.getApplication().settings.setValue('Collections' + '/' + self.getApplication().collectionSettingsName + '/' + 'displayedConfigFields',self.displayedConfigFields)
        else: # QVariant bug: cannot store empty list, save 0 instead
            self.getApplication().settings.setValue('Collections' + '/' + self.getApplication().collectionSettingsName + '/' + 'displayedConfigFields',0)

    def changeResultViewMode(self,newViewMode):
        self.studyController.dataAboutToBeChanged()
        self.resultViewMode = newViewMode
        self.studyController.dataHasBeenChanged()
        # save that to settings
        if self.getApplication().currentDatabase is not None and self.getApplication().currentRunCollection is not None:
            self.getApplication().settings.setValue('Collections' + '/' + self.getApplication().collectionSettingsName + '/' + 'resultViewMode',newViewMode)

    def columnWidthsChanged(self,newColumnWidths):
        self.columnWidths = newColumnWidths
        print('New colulmn widths (begin saved):',newColumnWidths)
        self.getApplication().settings.setValue('Collections' + '/' + self.getApplication().collectionSettingsName + '/' + 'columnWidths',newColumnWidths)

    # update the current column widths with defaults where necessary
    def updateColumnWidths(self):
        initialColumnWidths = { f: self.DefaultColumnWidth for f in self.displayedFields() }
        initialColumnWidths.update(self.columnWidths)
        self.columnWidths = initialColumnWidths

    
