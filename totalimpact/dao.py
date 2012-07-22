import pdb, json, uuid, couchdb, time, copy, logging, os, re, threading, redis
from couchdb import ResourceNotFound, PreconditionFailed
from totalimpact import default_settings
import requests

# set up logging
logger = logging.getLogger("ti.dao")
lock = threading.Lock()

class DbUrl(object):
    
    def __init__(self, url):
        self.full = url
        
    def get_username(self):
        m = re.search("https://([^:]+)", self.full)
        return m.group(1)

    def get_password(self):
        m = re.search(":[^:]+:([^@]+)", self.full)
        return m.group(1)
    
    def get_base(self):
        m = re.search("@(.+)", self.full)
        return "https://" + m.group(1)
        

class Dao(object):

    def __init__(self, db_url, db_name):
        '''sets up the data properties and makes a db connection'''

        self.couch = couchdb.Server(url=db_url)
        self.url = DbUrl(db_url)
        self.db_name = db_name

        # setup redis. this should go elsewhere, eventually.
        self.redis = redis.from_url(os.getenv('REDISTOGO_URL'))

        try:
            self.db = self.couch[ db_name ]
        except (ResourceNotFound):
            self.create_db(db_name)
        except LookupError:
            raise LookupError("CANNOT CONNECT TO DATABASE, maybe doesn't exist?")
        
        self.bump = self.db.resource("_design", "queues", "_update", "bump-providers-run")

       
    def delete_db(self, db_name):
        self.couch.delete(db_name);


        
        
    def update_design_doc(self):
        design_doc = {
            "_id": "_design/queues",
            "language": "javascript",
            "views": {
                "by_alias": {},
                "by_tiid_with_snaps": {},
                "by_type_and_id": {},
                "needs_aliases": {},
            }
        }

        for view_name in design_doc["views"]:
            file = open('./config/couch/views/{0}.js'.format(view_name))
            design_doc["views"][view_name]["map"] = file.read()        

        logger.info("overwriting the design/queues doc with the latest version in dao.")
        logger.debug("overwriting the design/queues doc with this, from dao: " + str(design_doc))
        
        try:
            current_design_doc_rev = self.db["_design/queues"]["_rev"]
            design_doc["_rev"] = current_design_doc_rev
        except ResourceNotFound:
            logger.info("brand new db; there's no design/queues doc. That's fine, we'll make it.")
            
        self.db.save(design_doc)
        logger.info("saved the new design doc.")


    def create_db(self, db_name):
        '''makes a new database with the given name.
        uploads couch views stored in the config directory'''

        try:
            self.db = self.couch.create(db_name)
            self.db_name = db_name
        except ValueError:
            print("Error, maybe because database name cannot include uppercase, must match [a-z][a-z0-9_\$\(\)\+-/]*$")
            raise ValueError
        
        self.update_design_doc()

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

       
    def view(self, viewname):
        return self.db.view(viewname)

    def create_collection(self):
        return self.create_item()

    def update_collection(self):
        return self.update_item()
        
    def delete(self, id):
        doc = self.db.get(id)
        self.db.delete(doc)
        return True

    def create_new_db_and_connect(self, db_name):
        '''Create and connect to a new db, deleting one of same name if it exists.

        TODO: This is only used for testing, and so should move into test code'''
        try:
            self.delete_db(db_name)
        except LookupError:
            pass # no worries, it doesn't exist but we don't want it to

        self.create_db(db_name)

    def __getstate__(self):
        '''Returns None when you try to pickle this object.

        Otherwise a threadlock from couch prevents pickling of other stuff that
        may contain this object.'''

        return None

    def bump_providers_run(self, item_id, provider_name, tries=0):
        providers_run_count = self.redis.incr(item_id)
        logger.info("bumped providers_run with {provider_name} for {id}. {providers_run_count} run so far.".format(
            provider_name=provider_name,
            id=item_id,
            providers_run_count=providers_run_count
        ))
        return int(providers_run_count)

    def get_providers_run_count(self, item_id):
        r = self.redis.get(item_id)
        logger.debug("getting providers run count for {id}: it's {num}".format(
            id=item_id,
            num=r
        ))
        if r is None:
            return 0
        else:
            return int(r)

    def reset_providers_run_count(self, item_id):
        logger.debug("resetting providers_run count to zero for "+item_id)
        self.redis.set(item_id, 0)


