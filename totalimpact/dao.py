import pdb
import json
import uuid
import couchdb
import time

class Dao(object):
    '''the dao that can be named is not the true dao'''
    __type__ = None

    def __init__(self, config):
        '''sets up the data properties and makes a db connection'''
        self.config = config
        
        self.couch = couchdb.Server( url = self.config.db_url )
        self.couch.resource.credentials = ( self.config.db_adminuser, self.config.db_password )

    def connect(self, db_name=False):
        '''connect to an extant database. 
        Fails if the database doesn't exist'''
        
        if db_name:
            self.config.db_name = db_name

        if self.db_exists(self.config.db_name) == False:
            raise LookupError("database doesn't exist")
        self.db = self.couch[ self.config.db_name ]


    def create_db(self, db_name):
        self.couch.create( db.name )
        
    def db_exists(self, db_name):
        try:
            self.couch[db_name]
            return True
        except:
            return False

    def delete_db(self, db_name):
        self.couch.delete(db_name);

    def create_db(self, db_name):
        '''makes a new database with the given name.
        uploads couch views stored in the config directory'''
        view = self.config.db_views
        for view_name in self.config.db_views['views']:
            file = open('./config/couch/views/{0}.js'.format(view_name))
            view["views"][view_name]["map"] = file.read()

        self.db = self.couch.create(db_name)
        self.db.save( view )
        return True

  
    @property
    def json(self):
        return json.dumps(self.data,sort_keys=True,indent=4)

    def get(self,_id):
        if (_id):
            return self.db.get(_id)
        else:
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
        if viewname == '_all_docs':
            fullpath = '/' + self.config.db_name + '/' + viewname
        else:
            fullpath = '/' + self.config.db_name + '/_design/queues/_view/' + viewname.replace('queues/','') + '?'
        for key,val in kwargs.iteritems():
            if not fullpath.endswith('&'): fullpath += '&'
            fullpath += key + '=' + urllib.quote_plus(json.dumps(val))
        c =  httplib.HTTPConnection(host)
        c.request('GET', fullpath)
        result = c.getresponse()
        return json.loads(result.read())
        
    def save_section(self, data, subject, _id=False):

        # first get the doc, or make it
        doc = self.get(_id)
        if doc == None:
            doc = {}
            doc['created'] = time.time()
            doc["_id"] = uuid.uuid4().hex
            doc[subject] = {}
        
        # merge the old and new data in the relevant section
        new_section = dict(doc[subject].items() + data.items())
        doc[subject] = new_section
        
        if 'last_modified' not in doc:
            doc['last_modified'] = 0
        else:
            doc['last_modified'] = time.time()

        self.db.save(doc)

        try:
            return self.save(doc)
        except:
            # try the save again, probably an update conflict.
            return False
        
    def delete(self):
        try:
            self.db.delete(self.data)
            self.data = {}
            return True
        except:
            # log the delete error? action on doc update conflict?
            return False


