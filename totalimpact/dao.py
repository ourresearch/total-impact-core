import json, uuid, couchdb, time, logging, os, re, redis
from couchdb import ResourceNotFound, PreconditionFailed

from totalimpact.utils import Retry

# set up logging
logger = logging.getLogger("ti.dao")

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
        design_docs = [
            {
                "_id": "_design/queues",
                "language": "javascript",
                "views": {
                    "by_alias": {},
                    "by_type_and_id": {},
                    "latest-collections": {},
                }
            },
            {
                "_id": "_design/collections_with_items",
                "language": "javascript",
                "views": {
                    "collections_with_items": {}
                }
            },
            {
                "_id": "_design/reference-sets",
                "language": "javascript",
                "views": {
                    "reference-sets": {}
                }
            },
            {
                "_id": "_design/provider_batch_data",
                "language": "javascript",
                "views": {
                    "by_alias_provider_batch_data": {}
                }
            }
        ]

        for design_doc in design_docs:
            design_doc_name = design_doc["_id"]
            for view_name in design_doc["views"]:
                with open('./config/couch/views/{0}.js'.format(view_name)) as f:
                    design_doc["views"][view_name]["map"] = f.read()

            logger.info("overwriting the design doc with the latest version in dao.")
            
            try:
                current_design_doc_rev = self.db[design_doc_name]["_rev"]
                design_doc["_rev"] = current_design_doc_rev
            except ResourceNotFound:
                logger.info("No existing design doc found for {design_doc_name}. That's fine, we'll make it.".format(
                    design_doc_name=design_doc_name))
                
            self.db.save(design_doc)
            logger.info("saved the new design doc {design_doc_name}".format(
                design_doc_name=design_doc_name))


    def create_db(self, db_name):
        '''makes a new database with the given name.
        uploads couch views stored in the config directory'''

        try:
            self.db = self.couch.create(db_name)
            self.db_name = db_name
        except ValueError:
            print("Error, maybe because database name cannot include uppercase, must match [a-z][a-z0-9_\$\(\)\+-/]*$")
            raise ValueError
        
        # don't update the design docs because it risks adding an accidental change and 
        ## triggering an app-halting reindex
        #self.update_design_doc()

    @property
    def json(self):
        return json.dumps(self.data, sort_keys=True, indent=4)

    @Retry(3, Exception, 0.1)
    def get(self,_id):
        if (_id):
            return self.db.get(_id)
        else:
            return None

    @Retry(3, Exception, 0.1)
    def save(self, doc):
        if "_id" not in doc:
            raise KeyError("tried to save doc with '_id' key unset.")
        response = self.db.save(doc)
        logger.info("dao saved %s" %(doc["_id"]))
        return response

       
    def view(self, viewname):
        return self.db.view(viewname)

    @Retry(3, Exception, 0.1)
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
        return None


