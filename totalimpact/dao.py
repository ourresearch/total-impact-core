import json
import uuid
import couchdb

class Dao(object):

    def __init__(self, **kwargs):
        # read these from config
        self.couch_url = "http://localhost:5984/"
        self.couch_db = "bibsoup"
        
        self.couch = couchdb.Server(url=couch_url)
        self.db = couch[couch_db]
        self.data = dict(kwargs)
        
    def id(self):
        '''Get id of this object.'''
        return "id"
        
    def version(self):
        return "version"

    def save(self):
        '''Save to backend storage.'''
        return "saved"

    def get(self):
        '''Retrieve object by id.'''
        return "thing"
    
    def json(self):
        return json.dumps(self.data)
    
    def delete(self):
        '''delete this object'''
        return "deleted"


