from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# from PyQt4 import QtCore, QtGui

import pymongo
import bson
import numpy as np

# This class represents a connection to a mongodb server. It offers just a few interface functions
# allowing to access "databases" and "collections"
class DbConnection(object):
    def __init__(self,application):
        self.application = application
        self.mongoClient = None

    def connect(self,uri):
        self.mongoClient = pymongo.mongo_client.MongoClient(uri,socketTimeoutMS=50000) # TODO allow for remote connection?
        # may raise Exception

    def getDatabaseNames(self):
        return sorted(self.mongoClient.database_names())

    # go through collections and return 
    # db may be a string or a database object
    def getCollectionNames(self,db):
        if type(db) == str or type(db) == unicode:
            db = getDatabase(db)
        return db.collection_names()

    def getDatabase(self,name):
        return self.mongoClient[name]

    def getCollection(self,db,name):
        # db may be a string or a database object
        if type(db) == str or type(db) == unicode:
            db = getDatabase(db)
        return db[name]

    def deleteCollection(self,dbName,collectionName):
        # note that this one should be called for ALL associated collections!
        db = self.getDatabase(dbName)
        db.drop_collection(collectionName)
