import sys

from PyQt5 import QtCore, QtGui, QtWidgets

import time
import re

import pymongo
import bson

from . import Config
from . import DetailsDialog

# The StudyModel contains all information about the currently displayed "study", where a study is essentially
# a list of experiments. Note that some display information is permanently saved with the collection and therefore
# also part of the model.
# The model accesses the database, but is otherwise rather passive, control commands are issued by the StudyController.
# Note that the "model" for the experiment list (as part of Qts model/view framework) is separate from StudyModel -
# it is the ExperimentListModel, which also draws on the StudyModel and serves as basis for ExperimentListView.
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
    ## ACCESSORS
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

    ########################################################
    ## DISPLAY FUNCTIONS
    ########################################################

    def changeSortOrder(self,newSortOrder):
        self.currentSortOrder = newSortOrder[0:6]

    def changeDisplayedFieldList(self,newDisplayedFields):
        # now change layout
        self.displayedConfigFields = newDisplayedFields
        self.updateColumnWidths()

        # TODO tell sort dialog
        # write config
        if len(self.displayedConfigFields) > 0:
            self.getApplication().settings.setValue('Collections' + '/' + self.getApplication().collectionSettingsName + '/' + 'displayedConfigFields',self.displayedConfigFields)
        else: # QVariant bug: cannot store empty list, save 0 instead
            self.getApplication().settings.setValue('Collections' + '/' + self.getApplication().collectionSettingsName + '/' + 'displayedConfigFields',0)

    def changeResultViewMode(self,newViewMode):
        self.resultViewMode = newViewMode
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

    ########################################################
    ## MAIN MODEL GENERATION - restting, querying, resorting
    ########################################################

    # Resets all content of this view, emits suitable signals to the fieldView and the sort dialog.
    # TODO doku
    def reset(self):
        # get current collection from application, create a query, read all configs to determine the possible headers
        # empty the collection view (and related views) if no collection is chosen
        if self.getApplication().currentRunCollection is None:
            assert self.getApplication().currentRunCollectionName is None

            self.initEmpty()

            self.valid = False
        else:
            # retrieve settings for this collection 
            lastDispFields = self.getApplication().settings.value('Collections' + '/' + self.getApplication().collectionSettingsName + '/' + 'displayedConfigFields')
            lastSortOrder = self.getApplication().settings.value('Collections' + '/' + self.getApplication().collectionSettingsName + '/' + 'sortOrder')
            lastViewMode = self.getApplication().settings.value('Collections' + '/' + self.getApplication().collectionSettingsName + '/' + 'resultViewMode')
            lastQueryText = self.getApplication().settings.value('Collections' + '/' + self.getApplication().collectionSettingsName + '/' + 'lastQueryText')
            lastColumnWidths = self.getApplication().settings.value('Collections' + '/' + self.getApplication().collectionSettingsName + '/' + 'columnWidths')

            # first make headers
            self.allConfigFields,self.resultLength = self.getHeaderInfo()
            self.allConfigFields = list(self.allConfigFields) 

            self.resultFields = [ 'Result %d' % m for m in range(1,self.resultLength + 1) ]

            # set displayed fields
            if lastDispFields is not None:
#                 if lastDispFields.toInt()[1]:
#                     assert lastDispFields.toInt()[0] == 0
#                     self.displayedConfigFields = []
#                 else:
#                     # filter to make sure the fields actually still exist
                    self.displayedConfigFields = [str(x) for x in lastDispFields if str(x) in self.allConfigFields]

            else:
                self.displayedConfigFields = list(self.allConfigFields)

            # query with empty dict - show everything. This fills self.collectionData
            if lastQueryText is not None: 
                self.performQuery(lastQueryText) 
            else:
                self.performQuery("")
                
            # set view mode
            if lastViewMode is not None:
                self.resultViewMode = int(lastViewMode)
            else:
                self.resultViewMode = self.ResultViewRaw

            # set sort order
            if lastSortOrder is not None:
                self.currentSortOrder = lastSortOrder
                for pos in range(len(self.currentSortOrder)):
                    self.currentSortOrder[pos] = str(self.currentSortOrder[pos])
            else:
                self.currentSortOrder = self.displayedConfigFields

            self.currentSortOrder = self.currentSortOrder[0:6]

            # set column widths
            if lastColumnWidths is not None:
                self.columnWidths = lastColumnWidths
            else:
                self.columnWidths = {}
            self.updateColumnWidths()

            self.valid = True
        return self.valid

    # Obtain header info when a new collection is displayed
    def getHeaderInfo(self):
        entries = self.queryDatabase({},projection=['config'])
        allConfigFields = set()
        # add config entries to displayed headers, and determine the length of "result"
        resultLength = -1
        for entry in entries:
            for option in entry['config']:
                allConfigFields.add(str(option))
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
    # This function raises a ValueErro if something is wrong
    def validateQuery(self,queryText):

# # # # #         print('Call to validateQuery, text is ---%s---' % queryText)
        # HELPER FUNCTIONS

        # possibly convert a string to a number
        def possiblyConvert(x):
            try:
                cnum = int(x)
                return cnum
            except ValueError:
                try:
                    cnum = float(x)
                    return cnum
                except:
                    val = str(x)
                    if val.upper() == 'NONE':
                        return None
                    elif val.upper() == 'TRUE':
                        return True
                    elif val.upper() == 'FALSE':
                        return False
                    else:
                        return val

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

        # parse the condition that a fieldname does not exist
        def parseNonExist(fieldName,content):
            resultDict = { fieldName: { '$exists': False } }
            return resultDict


        # MAIN PART: parse input, line by line

        # This will be the resulting query. It will have a single key ['$and'], joining one sub-dictionary for each line.
        # This is a requirement to make more complicated mongo queries work.
        resultDict = { '$and': [] }
        processedResultFieldNames = []
        
        lines = str(queryText).split('\n')
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
            elif re.match(r'^\s*---\s*$',content):
                thisResultDict = parseNonExist(fieldName,content)
            else:   
                # simple content
                content = possiblyConvert(content)

                thisResultDict = { fieldName: content }
            resultDict['$and'].append(thisResultDict)

            processedResultFieldNames.append(fieldName)

        return resultDict if len(resultDict['$and']) > 0 else {}

    # perform a query and convert data into our format (includes flattening config dicts)
    # this function receives a query dict in mongo format (may be {})
    def queryDatabase(self,queryDict,projection=[]):
        def determineEntryFormat(entry):
            # to be extended
            if format in entry and entry['format'] == 'MongoObserver-0.7.0':
                return '070'
            else:
                return 'old'

        def parseConfig(cfgDict):
            def recursivelyFlattenDict(prefix,dct):
                result = {}
                for key,val in dct.items():
                    thisPrefix = prefix + '.' + key if prefix != '' else key
                    if type(val) is dict:
                        result.update(recursivelyFlattenDict(thisPrefix,val))
                    else:
                        result[thisPrefix] = val
                return result
    
            return recursivelyFlattenDict('',cfgDict)

        def parseSingleEntry(entry):
            def get_size(obj, seen=None):
                """Recursively finds size of objects"""
                size = sys.getsizeof(obj)
                if seen is None:
                    seen = set()
                obj_id = id(obj)
                if obj_id in seen:
                    return 0
                # Important mark as seen *before* entering recursion to gracefully handle
                # self-referential objects
                seen.add(obj_id)
                if isinstance(obj, dict):
                    size += sum([get_size(v, seen) for v in obj.values()])
                    size += sum([get_size(k, seen) for k in obj.keys()])
                elif hasattr(obj, '__dict__'):
                    size += get_size(obj.__dict__, seen)
                elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
                    size += sum([get_size(i, seen) for i in obj])
                return size

            
            # entry keys (new version): [u'status', u'info', u'experiment', u'format', u'artifacts', u'start_time', u'captured_out', u'host', u'meta', u'command', u'result', u'heartbeat', u'_id', u'config', u'resources']
            # in the old version, some keys are optional
            result = {}

            if 'status' in entry:
                result['status'] = entry['status']
            if 'host' in entry:
                result['host'] = entry['host']
            if 'meta' in entry:
                result['meta'] = entry['meta']
            if 'command' in entry:
                result['command'] = entry['command']
            if 'start_time' in entry:
                result['start_time'] = entry['start_time']
            if 'stop_time' in entry:
                result['stop_time'] = entry['stop_time']
            if 'heartbeat' in entry:
                result['heartbeat'] = entry['heartbeat']
            if 'fail_trace' in entry:
                result['fail_trace'] = entry['fail_trace']

            if 'captured_out' in entry:
                result['captured_out'] = entry['captured_out']

            if 'config' in entry:
                result['config'] = parseConfig(entry['config'])

            # ENORMOUS HACK FIXME TODO XXX
            if 'result' in entry:
                if type(entry['result']) is list:
                    result['result'] = entry['result'] 
                elif type(entry['result']) is dict:
                    result['result'] = entry['result']['py/tuple']

            if 'experiment' in entry:
                result['sources'] = entry['experiment']['sources']

            result['original_entry'] = entry

            result['_id'] = entry['_id']
#             print('Flabbergasting entry with id',result['_id'],'and size',get_size(entry))

            return result

        result = self.getApplication().currentRunCollection.find(queryDict,projection={'captured_out':False})
        result = self.getApplication().currentRunCollection.find(queryDict)
        parsedResult = []
        for entry in result:
            if not 'captured_out' in entry:
                entry['captured_out'] = 'NOT LOADED'
            thisParsedEntry = parseSingleEntry(entry)
            parsedResult.append(thisParsedEntry)

        return parsedResult

    # Make a new query and fill collectionData. May raise Exception is the query text is invalid.
    def performQuery(self,queryText):
        # convert query to mongo format, might raise exception
        query = self.validateQuery(queryText)
        # this has worked - go on

        # save this query to config
        self.lastQueryText = queryText
        self.getApplication().settings.setValue('Collections' + '/' + self.getApplication().collectionSettingsName + '/' + 'lastQueryText',queryText)

        # now actually perform query
        entries = self.queryDatabase(query)
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

            index = None # TODO remove
            tup = (index,entry)
            self.collectionData += [ tup ]
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

        self.collectionData = []

        for (pos,entry) in enumerate(allEntries):
            index = None # TODO remove
            tup = (index,entry)
            self.collectionData += [ tup ]

        # save to settings
        self.getApplication().settings.setValue('Collections' + '/' + self.getApplication().collectionSettingsName + '/' + 'sortOrder',self.currentSortOrder)

    
