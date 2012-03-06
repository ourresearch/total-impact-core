import json
import uuid
import couchdb


class Dao(object):

    def __init__(self, **kwargs):
        self.couch, self.db = connection()
        self.data = dict(kwargs)
        if not self.data.get('_id',False):
            self.data['_id'] = uuid.uuid4().hex

    def connection(self):
        # read these from config
        couch_url = 'http://localhost:5984/'
        couch_db = 'ti'
        
        couch = couchdb.Server(url=couch_url)
        db = couch[couch_db]
        return couch, db
        
    @property
    def id(self):
        '''Get id of this object.'''
        if self.doc:
            return self.doc.id
        else:
            self.data['_id'] = uuid.uuid(4).hex
            return self.data['_id']
        
    @property
    def version(self):
        if self.doc:
            return self.doc.rev
        else:
            return False

    @classmethod
    def save(cls):
        '''Save to backend storage.'''
        db.save(self.data)
        return "saved"

    @classmethod
    def get(cls,_id):
        '''Retrieve object by id.'''
        couch, db = connection()
        doc = db[_id]
        return cls(**doc)
    
    def json(self):
        return json.dumps(self.data)
    
    def delete(self):
        '''delete this object'''
        db.delete(self.id)
        return "deleted"


