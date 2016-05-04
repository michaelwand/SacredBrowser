from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from PyQt4 import QtCore, QtGui

import pymongo
import bson
import numpy as np

# This class represents a connection to a mongodb server. It offers just a few interface functions
# allowing to access "databases" and "collections"
class DbConnection(object):
    def __init__(self,application):
        self.application = application
        self.mongoClient = None

    def connect(self):
        # example URI: mongodb://localhost:27017
        lastMongoURI = self.application.settings.value('Global/LastMongoURI')
        if lastMongoURI is None:
            lastMongoURI = 'mongodb://localhost:27017'
        else:
            lastMongoURI = lastMongoURI.toString()

        (newMongoUri,ok) = QtGui.QInputDialog.getText(None,'Connect to database','Connection URI (example: mongodb://localhost:27017)',QtGui.QLineEdit.Normal,lastMongoURI)
        
        if ok: 
            self.application.settings.setValue('Global/LastMongoURI',str(newMongoUri))
            try:
                self.mongoClient = pymongo.mongo_client.MongoClient(str(newMongoUri),socketTimeoutMS=50000) # TODO allow for remote connection?
            except pymongo.errors.ConnectionFailure as e:
                QtGui.QMessageBox.critical(None,'Could not connect to database',
                        'Database connection could not be established. Pymongo raised error:\n%s' % str(e))
                return False

            return True
        else:
            return False

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
