import pdb, json, uuid, couchdb, time
from totalimpact.core import app

class Dao(object):

    def __init__(self, db_name):
        '''sets up the data properties and makes a db connection'''
        self.db_url = "http://localhost:5984/"
        self.db_name = db_name
        
        self.couch = couchdb.Server( url = self.db_url )
        try:
            self.couch.resource.credentials = ( app.config["DB_ADMINUSER"], app.config["DB_PASSWORD"] )
        except KeyError:
            # no admin user and password specified
            pass

        if not self.db_exists(self.db_name):
            self.create_db(self.db_name)
        self.connect_db(self.db_name)

    def connect_db(self, db_name):
        '''connect to an extant database. 
        Fails if the database doesn't exist'''

        if not self.db_exists(db_name):
            raise LookupError("database doesn't exist")
        self.db = self.couch[ db_name ]
        self.db_name = db_name
       
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
        view = {
                    "_id": "_design/queues",
                    "language": "javascript",
                    "views": {
                        "metrics": {},
                        "aliases": {}
                        } 
                    }
        for view_name in view["views"]:
            file = open('./config/couch/views/{0}.js'.format(view_name))
            view["views"][view_name]["map"] = file.read()

        try:
            self.db = self.couch.create(db_name)
        except ValueError:
            print("Error, maybe because database name cannot include uppercase, must match [a-z][a-z0-9_\$\(\)\+-/]*$")
            raise ValueError
        self.db.save( view )
        return True

    @property
    def json(self):
        return json.dumps(self.data, sort_keys=True, indent=4)

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
        host = str(self.db_url).rstrip('/').replace('http://','')
        if viewname == '_all_docs':
            fullpath = '/' + self.db_name + '/' + viewname
        else:
            fullpath = '/' + self.db_name + '/_design/queues/_view/' + viewname.replace('queues/','') + '?'
        for key,val in kwargs.iteritems():
            if not fullpath.endswith('&'): fullpath += '&'
            fullpath += key + '=' + urllib.quote_plus(json.dumps(val))
        c =  httplib.HTTPConnection(host)
        c.request('GET', fullpath)
        result = c.getresponse()
        result_json = json.loads(result.read())

        if (u'reason', u'missing_named_view') in result_json.items():
            raise LookupError

        return result_json
    
    def create_item(self, data, id):
        doc = {}
        for d in data:
            doc[d] = data[d]

        doc["_id"] = id
        doc['created'] = time.time()
        doc['last_modified'] = 0
        return self.db.save(doc)

    def update_item(self, data, id):
        doc = self.get(id)
        if not doc:
            raise LookupError

        for key in data:
            try:
                # add dict items,but overwrite identical keys
                new = dict(doc[key].items() + data[key].items())
                doc[key] = new
            except AttributeError:
                if data[key] is not None:
                    doc[key] = data[key]

        doc['last_modified'] = time.time()
        print(doc)

        # FIXME handle update conflicts properly
        return self.db.save(doc)

    def create_collection(self):
        return self.create_item()

    def update_collection(self):
        return self.update_item()
        
    def delete(self, id):
        doc = self.db[id]
        self.db.delete(doc)
        return True

    def create_new_db_and_connect(self, db_name):
        '''Create and connect to a new db, deleting one of same name if it exists.'''
        if self.db_exists(db_name):
            self.delete_db(db_name)
        self.create_db(db_name)
        self.connect_db(db_name)



