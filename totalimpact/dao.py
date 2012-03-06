import json
import uuid
import couchdb

class Dao(object):
    __type__ = None

    def __init__(self, **kwargs):
        self.data = dict(kwargs)
        if '_id' not in self.data:
            self.data['_id'] = uuid.uuid4().hex

    @classmethod
    def connection(cls):
        # read these from config
        couch_url = 'http://localhost:5984/'
        couch_db = 'ti'
        
        couch = couchdb.Server(url=couch_url)
        db = couch[couch_db]
        return couch, db

    @property
    def id(self):
        '''Get id of this object.'''
        return self.data['_id']
        
    @property
    def version(self):
        return self.data.get('_rev',None)
        
    @classmethod
    def get(cls,_id):
        couch, db = cls.connection()
        doc = db[_id]
        if doc:
            return cls(**doc)
        else:
            return None

    def save(self):
        '''Save to backend storage.'''
        db.save(self.data)
        return "saved"
    
    @property
    def json(self):
        return json.dumps(self.data,sort_keys=True,indent=4)
    
    def delete(self):
        '''delete this object'''
        db.delete(self.id)
        return "deleted"


