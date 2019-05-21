# from . import BrowserState

from PyQt5 import QtCore

import enum
import collections
import re
import functools
import numbers
import sys

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

# # This badly hacked parser validate the 'filter' user input, adds some quotes 
# # and convert it into a dict, which is returned so that it can be passed on to PyMongo.collection.find
# # This function raises a ValueErro if something is wrong
# def validateQuery(queryText):
# 
#     # HELPER FUNCTIONS
# 
#     # possibly convert a string to a number
#     def possiblyConvert(x):
#         try:
#             cnum = int(x)
#             return cnum
#         except ValueError:
#             try:
#                 cnum = float(x)
#                 return cnum
#             except:
#                 val = str(x)
#                 if val.upper() == 'NONE':
#                     return None
#                 elif val.upper() == 'TRUE':
#                     return True
#                 elif val.upper() == 'FALSE':
#                     return False
#                 else:
#                     return val
# 
#     # parse an "or" condition, raise an exception if it goes wrong, return result dictionary to append to the
#     # mongo query if OK
#     def parseOrCondition(fieldName,content):
#         # first check if content has the form [ ... ]
# #             if not ((content.count('[') == 1) and (content.count(']') == 1)):
#         matchOb = re.match(r'^\s*\[([^\[\]]*)\]\s*$',content)
#         if matchOb is None:
#             raise ValueError('Illegal 'or' command (required format [ ... ]) in line %d' % lX)
# 
#         subContent = matchOb.groups()[0]
#         subContentData = subContent.split(',')
# 
#         if len(subContentData) == 1:
#             # not a real 'or' since just one alternative is given!
#             singleSubContent = possiblyConvert(subContentData[0])
#             resultDict = { fieldName: singleSubContent }
#         else:
#             # make 'or' query
#             resultDict = { '$or': [ { fieldName: possiblyConvert(val.strip()) } for val in subContentData ] }
#         
#         return resultDict
# 
#     # parse a regexp condition, raise an exception if it goes wrong, return result dictionary to append to the
#     # mongo query if OK
#     def parseRegexp(fieldName,content):
#         # first check if content has the form [ ... ]
# #             if not ((content.count('[') == 1) and (content.count(']') == 1)):
#         matchOb = re.match(r'^\s*/(.*)/\s*$',content)
#         if matchOb is None:
#             raise ValueError('Illegal regexp (required format / ... /) in line %d' % lX)
# 
#         subContent = matchOb.groups()[0]
# 
#         resultDict = { fieldName: { '$regex': subContent.strip() } }
# 
#         return resultDict
# 
#     # parse the condition that a fieldname does not exist
#     def parseNonExist(fieldName,content):
#         resultDict = { fieldName: { '$exists': False } }
#         return resultDict
# 
# 
#     # MAIN PART: parse input, line by line
# 
#     # This will be the resulting query. It will have a single key ['$and'], joining one sub-dictionary for each line.
#     # This is a requirement to make more complicated mongo queries work.
#     resultDict = { '$and': [] }
#     processedResultFieldNames = []
#     
#     lines = str(queryText).split('\n')
#     for (lX,line) in enumerate(lines):
#         # skip empty lines and comments
#         if re.match(r'^\s*$',line) or re.match(r'^\s*#.*$',line):
#             continue
# 
#         # basic parsing - split field: content
# #                 (fieldName,content) = line.split(':')
#         colPos = line.find(':')
#         if colPos == -1:
#             raise ValueError('Line %d must contain at least one colon (:)')
#         fieldName = line[0:colPos]
#         content = line[colPos+1:]
# 
#         fieldName = fieldName.strip()
#         content = content.strip()
#         
#         # interpret context, several cases ('or' condition, regexp, normal text)
#         fieldName = str('config.' + fieldName)
#         if fieldName in processedResultFieldNames:
#             raise ValueError('Key %s specified twice in line %d' % (fieldName,lX))
# 
#         if re.match(r'^\s*\[.*\]\s*$',content):
#             thisResultDict = parseOrCondition(fieldName,content)
#         elif re.match(r'^\s*/.*/\s*$',content):
#             thisResultDict = parseRegexp(fieldName,content)
#         elif re.match(r'^\s*---\s*$',content):
#             thisResultDict = parseNonExist(fieldName,content)
#         else:   
#             # simple content
#             content = possiblyConvert(content)
# 
#             thisResultDict = { fieldName: content }
#         resultDict['$and'].append(thisResultDict)
# 
#         processedResultFieldNames.append(fieldName)
# 
#     return resultDict if len(resultDict['$and']) > 0 else {}

# A change (to be transmitted to the model). Format: ChangeType is the type of the change,
# info is a tuple with the following elements:
# - Reset: info is None
# - Content: info is a list of changed rows
# - Insert: info is the position where the rows are inserted, the number of inserted rows
# - Remove: info is the position of the first removed row, and the remove count
# We permit info to have extra fields (currently used for the levenshtein hack)
class ChangeType(enum.Enum):
    Reset = 1
    Content = 2
    Insert = 3
    Remove = 4
ChangeData = collections.namedtuple('ChangeData',['tp','info'])

# Compute the minimum of vals, where each val is preprocessed with fun. If
# several elements attain the minimum, the first one is returned.
def ppmin(*vals,fun=lambda x:x):
    pps = [ fun(v) for v in vals ]
    minimum = min(pps)
    pos = pps.index(minimum)
    return vals[pos]


# Returns the complete list of ChangeData (Insert, Remove, Content) to get from s1 to s2, with as little 
# insertions/deletions/substitutions as possible. 
# The vertical axis represents the elements of s2, the horizontal axis represents s1. We iterate over
# the horizontal axis, thus we always have two columns (previous_col, last_col) in memory.
# Each element of previous_col or this_col is a list of editing steps needed to get here; and we compare the length
# of the lists to get the cost. Note that it is not enough to only compute the Levenshtein cost, we need
# the actual editing steps.
# 
def levenshtein(s1, s2, equal = lambda a,b: a==b):
    print('---> Call to leveshtein, lenfgths:',len(s1),len(s2))
    target_len = len(s2) + 1
    this_col = None
    for col in range(len(s1)+1):
        previous_col = this_col
        this_col = [ None ] * target_len
        val1 = s1[col-1] if col > 0 else None

        # fill current column (this_col)
        for row in range(len(s2)+1):
            val2 = s2[row-1] if row > 0 else None

            # remark: when inserting or substituting, we add the element to be inserted or substituted
            # yes, this is a hack
            insert = this_col[row-1] + [ ChangeData(ChangeType.Insert,(row-1,1,[ val2 ])) ] if row > 0 else None
            delete = previous_col[row] + [ ChangeData(ChangeType.Remove,( row,1 )) ] if col > 0 else None
            if row == 0 or col == 0:
                subst = None
            else:
                subst = previous_col[row-1] + ( 
                        [ ChangeData(ChangeType.Content,([row - 1],[val2])) ] if not equal(val1,val2) else []
                        )
            if insert is None and delete is None and subst is None:
                # lower left corner == start!
                new_field = []
            else:
                new_field = ppmin(subst, insert, delete, fun = lambda x: len(x) if x is not None else sys.maxsize)
            this_col[row] = new_field

        # finished a row
        previous_col = this_col
    
    # final field
    return this_col[-1]


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
    
        # Dict saves all objects, the sorted keys are contained in keylist. 
        self._dict = {}
        self._keylist = []

    def list_keys(self):
        return self._keylist[:]

    #TODO all this naming is not so great
    def list_values(self):
        return [ self._dict[k] for k in self._keylist ]

    def update(self,new_keys):
        # first compute the required list of changes, and remember which objects will be deleted or created
        change_list = levenshtein(self._keylist,new_keys)
        delete_list = set(self._keylist) - set(new_keys)
        create_list = set(new_keys) - set(self._keylist)

        old_dict = self._dict.copy()

        # create objects which must be created
        for nk in create_list:
            ob = self._loader(nk)
            self._dict[nk] = ob

        # Now execute the changes, step by step. 

        for chg in change_list:
            self._pre_change_emit(chg)
            if chg.tp == ChangeType.Remove:
                pos = chg.info[0]
                cnt = chg.info[1]
                del self._keylist[pos:pos+cnt]
            elif chg.tp == ChangeType.Insert:
                pos = chg.info[0]
                cnt = chg.info[1]
                els = chg.info[2]
                assert cnt == len(els)
                assert type(els) is list
                self._keylist[pos:pos] = els # els is a list, note that insert won't work properly
            elif chg.tp == ChangeType.Content:
                positions = chg.info[0]
                elements = chg.info[1]
                assert len(positions) == len(elements)
                for p,e in zip(positions,elements): # note that positions might not be contiguous
                    self._keylist[p] = e
            self._post_change_emit(chg)

        # delete unneeded objects
        for ok in delete_list:
            self._deleter(self._dict[ok])
            del self._dict[ok]

        # At this point, self._keylist contains only keys which may remain. But they may be in the wrong order.

    def forall(self,fun):
        for x in self._dict.values():
            fun(x)

    def get_by_position(self,pos):
        key = self._keylist[pos]
        ob = self._dict[key]
        return (key,ob)

    def get_by_key(self,key):
        ob = self._dict[key]
        return (key,ob)
