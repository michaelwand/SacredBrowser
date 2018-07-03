
import string
import copy

# some global configuration obtions, currently hardcoded

# compareFunc creates a key to compare different database entries, with the goal of finding
# duplicates. Currently only removes the entry "seed".
# compareFunc = lambda dct: dct['config']
def compareFunc(dct):
    newDct = copy.copy(dct['config'])
    newDct.pop('seed',None)
    return newDct

# returns true is fieldname is the name of a database field which should by
# default not be shown
# def shouldBeSuppressed(fieldname):
#     return (string.upper(fieldname) in ['SEED','OUTFILENAME','TRAINDB','DEVDB','EVALDB'])
