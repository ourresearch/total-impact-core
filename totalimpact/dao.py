import pdb, json, uuid, couchdb, time, copy, logging
from couchdb import ResourceNotFound
from totalimpact import default_settings

# set up logging
logger = logging.getLogger("ti.dao")

class Dao(object):

    def __init__(self, db_url, db_name):
        '''sets up the data properties and makes a db connection'''

        self.couch = couchdb.Server(url=db_url)

        try:
            self.db = self.couch[ db_name ]
        except (ValueError, ResourceNotFound):
            self.create_db(db_name)
        except LookupError:
            raise LookupError("CANNOT CONNECT TO DATABASE, maybe doesn't exist?")
       
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

       
    def view(self, viewname, **kwargs):
        return self.db.view(viewname, kwargs)

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



