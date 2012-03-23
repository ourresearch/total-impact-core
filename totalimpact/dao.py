import json
import uuid
import couchdb
import time

from totalimpact.config import Configuration

_config = Configuration()

class Dao(object):
    '''the dao that can be named is not the true dao'''
    __type__ = None

    __config__ = _config

    def __init__(self, **kwargs):
        self._data = dict(kwargs)
        self._id = self._data.get('_id',None)
        self._version = self._data.get('_rev',None)
        self.config = self.__config__

    @classmethod
    def connection(cls):
        # on first connect, create if not existing
        couch = couchdb.Server( url = cls.__config__.db_url )
        couch.resource.credentials = ( cls.__config__.db_adminuser,cls.__config__.db_password )
        try:
            _db = couch[ cls.__config__.db_name ]
        except:
            _db = couch.create( cls.__config__.db_name )
            _db.save( cls.__config__.db_views )
        return _db

    @property
    def db(self):
        return self.connection()

    @property
    def data(self):
        return self._data
        
    @data.setter
    def data(self, val):
        self._data = val

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
        try:
            return cls(**cls.connection()[_id])
        except:
            return None

    def query(self,**kwargs):
        # pass queries through to couchdb, as per couchdb-python query
        # http://packages.python.org/CouchDB/client.html
        return self.db.query(**kwargs)
        
    def view(self, viewname, **kwargs):
        # error with couchdb view whenever there are params, so doing direct
        #return self.db.view(viewname, kwargs)
        import httplib
        import urllib
        host = str(self.config.db_url).rstrip('/').replace('http://','')
        db_name = self.config.db_name
        fullpath = '/' + db_name + '/_design/queues/_view/' + viewname.replace('queues/','') + '?'
        for key,val in kwargs.iteritems():
            if not fullpath.endswith('&'): fullpath += '&'
            fullpath += key + '=' + urllib.quote_plus(json.dumps(val))
        c =  httplib.HTTPConnection(host)
        c.request('GET', fullpath)
        result = c.getresponse()
        return json.loads(result.read())
        
    def save(self):
        if '_id' not in self.data:
            if self.id:
                self.data['_id'] = self.id            
            else:
                self.data['_id'] = uuid.uuid4().hex
                self.id = self.data['_id']
        if '_rev' not in self.data and self.version:
            self.data['_rev'] = self.version
            
        if 'created' not in self.data:
            self.data['created'] = time.time()
        
        if 'last_modified' not in self.data:
            self.data['last_modified'] = 0
        else:
            self.data['last_modified'] = time.time()

        try:
            self._id, self._version = self.db.save(self.data)
            self.data['_rev'] = self.version
            return self.id
        except:
            # log the save error? action on doc update conflict?
            return False
        
    def delete(self):
        try:
            self.data = {}
            self.db.delete(self.data)
            return True
        except:
            # log the delete error? action on doc update conflict?
            return False


