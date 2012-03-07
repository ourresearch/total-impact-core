import json
import uuid
import couchdb

class Dao(object):
    __type__ = None

    def __init__(self, **kwargs):
        self.couch, self.db = self.connection()
        self._data = dict(kwargs)
        self._id = self._data.get('_id',None)
        self._version = self._data.get('_rev',None)

    @property
    def data(self):
        return self._data
        
    @data.setter
    def data(self, obj):
        self._data = obj

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
        return self._id
    
    @id.setter
    def id(self,_id):
        self._id = _id
        
    @property
    def version(self):
        return self._version
        
    @property
    def json(self):
        return json.dumps(self.data,sort_keys=True,indent=4)

    @classmethod
    def get(cls,_id):
        couch, db = cls.connection()
        try:
            return cls(**db[_id])
        except:
            return None

    def save(self):
        if '_id' not in self.data:
            if self.id:
                self.data['_id'] = self.id            
            else:
                self.data['_id'] = uuid.uuid4().hex
                self.id = self.data['_id']
        self._id, self._version = self.db.save(self.data)
        self.data['_rev'] = self.version
        
    def delete(self):
        self.data = {}
        self.db.delete(self.data)


