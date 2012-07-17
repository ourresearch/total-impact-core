import os, requests, json, couchdb, time, sys, re, random
from totalimpact import dao
from time import sleep
import logging

# see http://wiki.pylonshq.com/display/pylonscookbook/Alternative+logging+configuration
logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='"%(asctime)s %(levelname)8s %(name)s - %(message)s"',
    datefmt='%H:%M:%S'
)
logging.getLogger("ti").setLevel(logging.INFO)
logger = logging.getLogger("ti.create_collection_test")

#quiet Requests' noisy logging:
requests_log = logging.getLogger("requests")
requests_log.setLevel(logging.WARNING)

# Don't get db from env variable because don't want to kill production by mistake
base_db_url = "https://app5492954.heroku:Tkvx8JlwIoNkCJcnTscpKcRl@app5492954.heroku.cloudant.com"
base_db = os.getenv("CLOUDANT_DB")
#base_db_url = "http://localhost:5984"
#base_db = "localdb"
#api_url = "http://total-impact-core-staging.herokuapp.com"
#webapp_url = "http://total-impact.org"
api_url = "http://localhost:5001"
webapp_url = "http://localhost:5000"





''' Test classes
*****************************************************************************'''

class DirectEntry:
    
    def get_plos_aliases(self):
        return [("doi", "10.1371/journal.pone.000" + str(x)) for x in range(2901, 3901)]
    
    def get_aliases(self, ranges):
        all_aliases = []
        for alias_type, count in ranges.iteritems():
            getter_name = "get_" + alias_type + "_aliases"
            aliases_of_this_type = getattr(self, getter_name)()
            all_aliases = all_aliases + aliases_of_this_type[0:count]
            
        logger.info("adding {0} aliases by direct entry.".format(len(all_aliases)))
        logger.debug("adding these aliases by direct entry: " + str(all_aliases))
        return all_aliases
            
            
            
class Widget:
    '''Emulates a single widget on the create_collection page; 
    
    feed it a provider name like "github" at instantiation, then run run a query 
    like jasonpriem to get all the aliases associated with that account
    '''
    query = None
    
    def __init__(self, provider_name):
        self.provider_name = provider_name
    
    def get_aliases(self, query):
        query_url = "{api_url}/provider/{provider_name}/memberitems?query={query}".format(
            api_url=api_url, 
            provider_name=self.provider_name,
            query=query
            )
        start = time.time()
        logger.info(
            "getting aliases from the {provider} widget, using url '{url}'"
            .format(provider=self.provider_name, url=query_url)
            )
        resp = requests.get(query_url)
        
        try:
            aliases = json.loads(resp.text)
        except ValueError:
            logger.warning("{provider} widget returned no json for {query}".format(
                provider=self.provider_name,
                query="query"
            ))
            aliases = []
            
        # anoyingly, some providers return lists-as-IDs, which must be joined with a comma
        aliases = [(namespace, id) if isinstance(id, str) 
            else (namespace, ",".join(id)) for namespace, id in aliases]
            
        logger.info("{provider} widget got {num_aliases} aliases from '{q}' in {elapsed} seconds.".format(
            provider = self.provider_name,
            num_aliases = len(aliases),
            q = query,
            elapsed = round(time.time() - start, 2),
        ))
            
        return aliases
    
    
    
class ReportPage:
    def __init__(self, collection_id):
        self.collection_id = collection_id
        start = time.time()
        logger.info("loading the report page for collection '{collection_id}'.".format(
            collection_id=collection_id
        ))
        request_url = "{webapp_url}/collection/{collection_id}".format(
            webapp_url=webapp_url,
            collection_id=collection_id
        )
        resp = requests.get(request_url)
        if resp.status_code == 200:
            self.tiids = self._get_tiids(resp.text)
            elapsed = time.time() - start
            logger.info("loaded the report page for '{collection_id}' in {elapsed} seconds.".format(
                collection_id=collection_id,
                elapsed=elapsed
            ))
        else:
            logger.warning("report page for '{collection_id}' failed to load! ({url})".format(
                collection_id = collection_id,
                url=request_url
            ))
    
        
    def _get_tiids(self, text):
        '''gets the list of tiids to poll. in the real report page, this is done
        via a 'tiids' javascript var that's placed there when the view constructs
        the page. this method parses the page to get them...it's brittle, though,
        since if the report page changes this breaks.'''
        
        m = re.search("var tiids = (\[[^\]]+\])", text)
        tiids = json.loads(m.group(1))
        return tiids


    def poll(self, max_time=50):
        
        logger.info("polling the {num_tiids} tiids of collection '{collection_id}'".format(
            num_tiids = len(self.tiids),
            collection_id = self.collection_id
        ))
        
        tiids_str = ",".join(self.tiids)
        still_updating = True
        tries = 0
        start = time.time()
        while still_updating:
                
            url = api_url+"/items/"+tiids_str
            resp = requests.get(url, config={'verbose': None})
            items = json.loads(resp.text)
            tries += 1
            
            currently_updating_flags = [True for item in items if item["currently_updating"]]
            num_currently_updating = len(currently_updating_flags)
            num_finished_updating = len(self.tiids) - num_currently_updating
            
            logger.info("{num_done} of {num_total} items done updating after {tries} requests.".format(
                num_done=num_finished_updating,
                num_total=len(self.tiids),
                tries=tries
            ))
            logger.debug("got these items back: " + str(items))

            elapsed = time.time() - start
            if resp.status_code == 200:
                logger.info("collection '{id}' finished updating in {elapsed} seconds.".format(
                    id=self.collection_id,
                    elapsed=elapsed
                ))
                still_updating = False
            elif elapsed > max_time:
                logger.error("max polling time ({max} secs) exceeded for collection '{id}'; giving up.".format(
                    max=max_time,
                    id=self.collection_id
                ))
                logger.error("these items in collection '{id}' didn't update: {item_ids}".format(
                    id=self.collection_id,
                    item_ids=", ".join([item["id"] for item in items if item["currently_updating"]])
                ))
                return False

            sleep(0.5)
            
            
            
            
class CreateCollectionPage:
    
    aliases = []
    
    def __init__(self):
        start = time.time()
        logger.info("loading the create-collection page")
        resp = requests.get(webapp_url+"/create")
        if resp.status_code == 200:
            elapsed = time.time() - start
            logger.info("loaded the create-collection page in {elapsed} seconds.".format(
                elapsed=elapsed
            ))
        else:
            logger.warning("create-collection page failed to load!".format(
                collection_id = collection_id
            ))
    
    def reload(self):
        self.aliases = []
    
    def enter_aliases_directly(self, ranges):
        direct_entry = DirectEntry()
        aliases_from_direct_entry = direct_entry.get_aliases(ranges)
        self.aliases = self.aliases + aliases_from_direct_entry
        return self.aliases
        
    def get_aliases_with_widgets(self, widgets_dict):
        for provider_name, query in widgets_dict.iteritems():
            widget = Widget(provider_name)
            aliases_from_this_widget = widget.get_aliases(query)
            self.aliases = self.aliases + aliases_from_this_widget
        return self.aliases
    
    def press_go_button(self):
        tiids = self._create_items()
        collection_id = self._create_collection(tiids)
        report_page = ReportPage(collection_id)
        report_page.poll()
                    
    def _create_items(self):
        start = time.time()
        logger.info("trying to create {num_aliases} new items.".format(
            num_aliases = len(self.aliases)
        ))
        query = api_url + '/items'
        data = json.dumps(self.aliases)
        resp = requests.post(
            query, 
            data=data,
            headers={'Content-type': 'application/json'}
            )
        
        try:
            tiids = json.loads(resp.text)
        except ValueError:
            logger.warning("POSTing {query} endpoint returned no json (body: {data}) ".format(
                query=query,
                data=data
            ))
            raise ValueError
        
        logger.info("created {num_items} items in {elapsed} seconds.".format(
            num_items = len(self.aliases),
            elapsed = round(time.time() - start, 2)
            ))
            
        logger.debug("created these new items: " + str(tiids))
            
        return tiids
    
    def _create_collection(self, tiids):
        start = time.time()
        url = api_url+"/collection"
        collection_name = "test"

        logger.info("creating collection with {num_tiids} tiids".format(
            num_tiids = len(tiids)
        ))
        logger.debug("creating collection with these tiids: " + str(tiids))
        
        resp = requests.post(
            url,
            data = json.dumps({
                "items": tiids, 
                "title": collection_name
            }),
            headers={'Content-type': 'application/json'}
        )
        collection_id = json.loads(resp.text)["id"]
        
        logger.info("created collection '{id}' with {num_items} items in {elapsed} seconds.".format(
            id=collection_id,
            num_items = len(self.aliases),
            elapsed = round(time.time() - start, 2)
            ))        
            
        return collection_id
    
    def clean_db(self):
        
        start = time.time()
        
        # this is a painfully inefficient way to do this...
        # TODO rewrite DAO to extend python-couchdb, not encapsulate it.
        mydao = dao.Dao(base_db_url, base_db)
        mydao.delete_db(base_db)
        mydao.create_db(base_db)

        logger.info("deleted and remade the old 'ti' db in {elapsed} seconds".format(
            elapsed=round(time.time() - start, 2)
        ))
        

class IdSampler(object):
    
    def get(self, num):
        raise NotImplementedError
    

class DoiSampler(IdSampler):
    
    def get(self, num=1):
        url = "http://random.labs.crossref.org/dois?count="+str(num)
        r = requests.get(url)
        print r.text
        dois = json.loads(r.text)
        return dois
        
        

class GitHubUsernameSampler(IdSampler):
    
    db_url = "http://total-impact.cloudant.com/github_usernames"
    
    def get(self, num=1):
        rand_hex_string = hex(random.getrandbits(128))[2:-1] # courtesy http://stackoverflow.com/a/976607/226013
        req_url = self.db_url + '/_all_docs?include_docs=true&limit={limit}&startkey="{startkey}"'.format(
            limit=num,
            startkey=rand_hex_string
        )
        r = requests.get(req_url)
        json_resp = json.loads(r.text)

        usernames = [row["doc"]["actor"] for row in json_resp["rows"]]
        return usernames
        

class Report(object):
    pass


class User(object):
     
     def make_collection(self):
         pass
     
     def upate_collection(self):
         pass
     
     def check_collection(self):
         pass


''' Test code
*****************************************************************************'''
    
#TODO give test collections a memorable name
#TODO rename widget to importer

def run_test():
    start = time.time()
    logger.info("starting test.")
    ccp = CreateCollectionPage()
    ccp.clean_db()
    
    ccp.enter_aliases_directly({"plos": 5})
    ccp.get_aliases_with_widgets({"github": "jasonpriem"})
    ccp.press_go_button()
    
    logger.info("Finished test: collection took {elapsed} seconds".format(
        elapsed = round(time.time() - start, 2)
    ))
