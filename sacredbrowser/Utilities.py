from . import BrowserState

from PyQt5 import QtCore

import enum
import collections
import re
import functools
import numbers

# Parse a string entered by the user into a mongo query dictionary.
# Raises a ValueError if the query is malformed
def parse_query(queryText):

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

# This badly hacked parser validate the 'filter' user input, adds some quotes 
# and convert it into a dict, which is returned so that it can be passed on to PyMongo.collection.find
# This function raises a ValueErro if something is wrong
def validateQuery(queryText):

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

# # this class somewhat is outside the main information flow, it is currently handled by the ExperimentListModel
# class SortCache(QtCore.QObject):
#     # this class forces that two objects are always comparable
#     @functools.total_ordering
#     class SortItem:
#         def __init__(self,val):
#             self._val = val
# 
#         def __eq__(self,other):
#             try:
#                 return self._val == other._val
#             except TypeError:
#                 return False
# 
#         @staticmethod
#         def _get_sort_pos_by_type(val):
#             if val is None:
#                 return 0
#             if isinstance(val,str):
#                 return 1
#             if isinstance(val,numbers.Number):
#                 return 2
#             else:
#                 return 3
# 
#         def __le__(self,other):
#             try:
#                 return self._val <= other._val
#             except TypeError:
#                 my_pos = self._get_sort_pos_by_type(self._val)
#                 other_pos = self._get_sort_pos_by_type(other._val)
#                 return my_pos <= other_pos
# 
#     def __init__(self):
#         super().__init__()
# 
#         self._experiments = []
#         self._sort_order = []
# 
#         self._sorted_experiment_ids = []
# 
#         self._must_resort = True
# 
#     def get_sorted_experiment_ids(self):
#         if self._must_resort:
#             self._resort()
#             self._must_resort = False
# 
#         return self._sorted_experiment_ids
# 
#     def set_experiments(self,experiments):
#         self._experiments = experiments
#         self._must_resort = True
# 
#     def set_sort_order(self,sort_order):
#         self._sort_order = sort_order
#         self._must_resort = True
# 
#     def _resort(self):
#         # make a list which is suitable for sorting
#         filtered_exp_data = []
#         for exp in self._experiments:
#             this_item = []
#             for k in self._sort_order:
#                 try:
#                     this_el = exp.get_field(k)
#                 except KeyError:
#                     this_el = None
#                 this_item.append(self.SortItem(this_el))
#             # finally append the ID which we need at the end
#             this_item.append(exp.id())
#             filtered_exp_data.append(this_item)
# 
#         # perform sorting
#         filtered_exp_data.sort()
# 
#         self._sorted_experiment_ids = [ x[-1] for x in filtered_exp_data ]
# 
# #         print('SORTCACHE: List of IDs now',self._sorted_experiment_ids)
# 
# Process a result according to a specific view mode
def process_result(val,view_mode):
    if view_mode == BrowserState.GeneralSettings.ViewModeRaw:
        return str(val)
    elif view_mode == BrowserState.GeneralSettings.ViewModeRounded:
        try:
            return str(round(val,2))
        except Exception as e:
            print('Error rounding result %s, error was %s' % (val,str(e)))
            return str(val)
    elif view_mode == BrowserState.GeneralSettings.ViewModePercent:

        try:
            return str(round(val*100,2)) + '%'
        except Exception as e:
            print('Error computing percentage of result %s, error was %s' % (val,str(e)))
            return str(val)

class ChangeType(enum.Enum):
    Reset = 1
    Content = 2
    Insert = 3
    Remove = 4
ChangeData = collections.namedtuple('ChangeData',['tp','info'])

# This class implements a dictionary-style holder for (database) objects which always keeps a 
# specified order of the underlying objects, and which sends out signals about changes to the order. 
# The only way to change the content of the holder is the update() function, which takes a list of new keys to be loaded.
# The *emit callables are called with suitable ChangeData whenever a change is made.
class ObjectHolder:
    def __init__(self,*,pre_change_emit,post_change_emit,loader,deleter):
        # params
        self._pre_change_emit = pre_change_emit
        self._post_change_emit = post_change_emit
        self._loader = loader # should take a KEY
        self._deleter = deleter # should take an OBJECT, note that this is called BEFORE the object is removed from the internal list
    
        # internal functionality
        self._dict = {}
        self._keylist = []

    def list_keys(self):
        return self._keylist[:]

    #TODO all this naming is not so great
    def list_values(self):
        return list(self._dict.values())

    def update(self,new_keys):
        # Remove keys which are no longer needed.
        to_be_removed = set(self._keylist) - set(new_keys)

        for k in to_be_removed:
            pos = self._keylist.index(k)
            ob = self._dict[k]
            
            # perform change
            change_data = ChangeData(ChangeType.Remove,(pos,1))
            self._pre_change_emit(change_data)
            ob.delete()
            del self._dict[k]
            del self._keylist[pos]
            self._post_change_emit(change_data)


        # Add new keys. After this operation, new_keys will become the internal order
# # #         to_be_added = set(new_keys) - set(self._keylist)

#         # Need to insert new keys into keylist in their given order. Each new key is
#         # either to be inserted at keylist_position, or already present.
#         keylist_position = 0
#         for nk in new_keys:
#             if nk in self._keylist:
#                 # do nothing
#                 keylist_position += 1
#                 continue 
#             else:
#                 change_data = ChangeData(ChangeType.Insert,(keylist_position,1))
#                 self._pre_change_emit(change_data)
#                 ob = self._loader(nk)
#                 self._dict[nk] = ob
#                 self._keylist.insert(keylist_position,nk)
#                 self._post_change_emit(change_data)
#                 keylist_position += 1

        # at this point, self._keylist contains only keys which may remain. But they may be in the wrong order.


    def get_by_position(self,pos):
        key = self._keylist[pos]
        ob = self._dict[key]
        return (key,ob)

    def get_by_key(self,key):
        ob = self._dict[key]
        return (key,ob)
