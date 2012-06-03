import pdb, json, uuid, couchdb, time, copy
from totalimpact.tilogging import logging
from totalimpact import default_settings

# set up logging
logger = logging.getLogger(__name__)

class Dao(object):

    def __init__(self, db_name=None, db_url=None, db_username=None, db_password=None):
        '''sets up the data properties and makes a db connection'''
        self.db_name = db_name if db_name != None else default_settings.DB_NAME
        self.db_url = db_url if db_url != None else default_settings.DB_URL
        self.db_username = db_username if db_username != None else default_settings.DB_USERNAME
        self.db_password = db_password if db_password != None else default_settings.DB_PASSWORD
        
        self.couch = couchdb.Server( url = self.db_url )
        if self.db_username:
            self.couch.resource.credentials = ( 
                self.db_username, self.db_password
            )

        # connect to the db. It it doesn't exist, create it.
        try:
            self.connect_db(self.db_name)
        except LookupError:
            self.create_db(self.db_name)
            self.connect_db(self.db_name)
        except LookupError:
            raise LookupError("CANNOT CONNECT TO DATABASE, maybe doesn't exist?")

    def __getstate__(self):
        '''Returns None when you try to pickle this object.

        Otherwise a threadlock from couch prevents pickling of other stuff that
        may contain this object.'''

        return None

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
                        "by_alias": {},
                        "by_tiid_with_snaps": {},
                        "by_type_and_id": {},
                        "needs_aliases": {},
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

    def save(self, doc):
        try:
            doc["_id"] = doc["id"]
            del doc["id"]
        except KeyError:
            doc["_id"] = uuid.uuid1().hex
            logger.info("IN DAO MINTING A NEW ID ID %s" %(doc["_id"]))
        logger.info("IN DAO SAVING ID %s" %(doc["_id"]))
        retry = True
        while retry:
            try:
                response = self.db.save(doc)
                retry = False
            except couchdb.ResourceConflict, e:
                logger.info("Couch conflict %s, will retry" %(e))
                newer_doc = self.get(doc["_id"])
                doc["_rev"] = newer_doc["_rev"]
                time.sleep(0.1)
        logger.info("IN DAO SAVED ID %s" %(doc["_id"]))
        return response

    def save_and_commit(self, doc):
        ret = self.save(doc)
        self.db.commit()
        return ret


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

        #logger.info("IN DAO VIEW, HOST %s" %(host))
        #logger.info("IN DAO VIEW, FULLPATH %s" %(fullpath))

        c =  httplib.HTTPConnection(host)
        c.request('GET', fullpath)
        result = c.getresponse()
        result_json = json.loads(result.read())

        #logger.info("IN DAO VIEW, LEN RESPONSE %i" %(len(result_json)))
        #logger.info("IN DAO VIEW, RESPONSE KEYS %s" %(str(result_json.keys())))

        if (u'reason', u'missing_named_view') in result_json.items():
            raise LookupError

        return result_json
    

    def create_collection(self):
        return self.create_item()

    def update_collection(self):
        return self.update_item()
        
    def delete(self, id):
        doc = self.db.get(id)
        self.db.delete(doc)
        return True

    def create_new_db_and_connect(self, db_name):
        '''Create and connect to a new db, deleting one of same name if it exists.'''
        try:
            self.delete_db(db_name)
        except LookupError:
            pass # no worries, it doesn't exist but we don't want it to

        self.create_db(db_name)
        self.connect_db(db_name)



