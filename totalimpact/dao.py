import json, uuid, couchdb, time, logging, os, re, redis, urlparse
from couchdb import ResourceNotFound, PreconditionFailed
import psycopg2
import psycopg2.extras

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
            },
            {
                "_id": "_design/update",
                "language": "javascript",
                "views": {
                    "items_by_last_update_run": {}                    
                }
            },
            {
                "_id": "_design/doi_prefixes_by_last_update_run",
                "language": "javascript",
                "views": {
                    "doi_prefixes_by_last_update_run": {}                    
                }
            },
            {
                "_id": "_design/api_users_by_api_key",
                "language": "javascript",
                "views": {
                    "api_users_by_api_key": {}                    
                }
            },
            {
                "_id": "_design/registered_items_by_alias",
                "language": "javascript",
                "views": {
                    "registered_items_by_alias": {}                    
                }
            },
            {
                "_id": "_design/registered_tiids",
                "language": "javascript",
                "views": {
                    "registered_tiids": {}                    
                }
            },
            {
                "_id": "_design/gold_update",
                "language": "javascript",
                "views": {
                    "gold_update": {}                    
                }
            }            
        ]

        for design_doc in design_docs:
            design_doc_name = design_doc["_id"]
            for view_name in design_doc["views"]:
                with open('./config/couch/views/{0}.js'.format(view_name)) as f:
                    design_doc["views"][view_name]["map"] = f.read()

            #logger.info("overwriting the design doc with the latest version in dao.")
            
            try:
                current_design_doc_rev = self.db[design_doc_name]["_rev"]
                design_doc["_rev"] = current_design_doc_rev
            except ResourceNotFound:
                pass
                #logger.info("No existing design doc found for {design_doc_name}. That's fine, we'll make it.".format(
                #    design_doc_name=design_doc_name))
                
            self.db.save(design_doc)
            #logger.info("saved the new design doc {design_doc_name}".format(
            #    design_doc_name=design_doc_name))


    def create_db(self, db_name):
        '''makes a new database with the given name.'''

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


class PostgresDao(object):

    def __init__(self, connection_url):
        '''sets up the data properties and makes a db connection'''

        # just needs to be done once
        urlparse.uses_netloc.append("postgres")

        url = urlparse.urlparse(connection_url)
        dbname = url.path[1:]
        try:
            self.make_connection(url.hostname, dbname, url.username, url.password)
        except psycopg2.OperationalError:
            logger.info("OperationalError so trying to create database first")
            self.create_database(url.hostname, dbname, url.username, url.password)
            self.make_connection(url.hostname, dbname, url.username, url.password)


    def build_connection_string(self, hostname, dbname, username, password):
        connection_string = ""
        # don't add parts that are None
        if hostname:
            connection_string += " host=%s" %hostname
        if dbname:
            connection_string += " dbname=%s" %dbname
        if username:
            connection_string += " user=%s" %username
        if password:
            connection_string += " password=%s" %password
        return connection_string

    def create_database(self, hostname, new_dbname, username, password):
        blank_dbname = ""
        connection_string = self.build_connection_string(hostname, blank_dbname, username, password)
        conn = psycopg2.connect(connection_string)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("CREATE DATABASE " + new_dbname);
        cur.close()
        conn.close()

    def make_connection(self, hostname, dbname, username, password):
        connection_string = self.build_connection_string(hostname, dbname, username, password)
        self.conn = psycopg2.connect(connection_string)
        self.conn.autocommit = True
        logger.info("connected to postgres at {hostname} {dbname}".format(
            hostname=hostname, dbname=dbname))        
        return self.conn

    def create_tables(self):
        tables_string = """CREATE TABLE email (
        id text NOT NULL,
        created timestamptz,
        payload text NOT NULL,
        PRIMARY KEY (id))"""

        cur = self.get_cursor()
        try:
            cur.execute(tables_string);
        except psycopg2.ProgrammingError:
            # probably table already exists
            pass
        cur.close()

    def get_connection(self):
        return self.conn

    def get_cursor(self):
        # Dict Cursor (returns a Dict which can be referenced via named bracket access, or offset)
        return self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    def close(self):
        return self.conn.close()
       
    def save_email(self, email_dict):
        cur = self.get_cursor()
        cur.execute("""INSERT INTO email 
                        (id, created, payload) 
                        VALUES (%s, %s, %s)""",
            (email_dict["_id"], email_dict["created"], json.dumps(email_dict["payload"])))
        cur.close()
        return email_dict["_id"]

    def get_email(self, id):
        cur = self.get_cursor()
        cur.execute("SELECT * FROM email where id=%s", (id, ))
        rows = cur.fetchall()
        cur.close()
        return rows

