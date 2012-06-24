import os, requests, json, couchdb, time, sys
from totalimpact import dao
from time import sleep

import logging
requests_log = logging.getLogger("requests")
requests_log.setLevel(logging.WARNING)

# Don't get db from env variable because don't want to kill production by mistake
base_db_url = "https://app5492954.heroku:Tkvx8JlwIoNkCJcnTscpKcRl@app5492954.heroku.cloudant.com"
base_db = "ti"
#base_db_url = "http://localhost:5984"
#base_db = "localdb"

api_url = "http://total-impact-core-staging.herokuapp.com"
#api_url = "http://localhost:5001"

id_list = [("doi", "10.1371/journal.pone.000" + str(x)) for x in range(2901, 3901)]

def create_items(ids):
    ## Get all the tiids
    tiid_list = []
    for (namespace, nid) in ids:
        get_tiid_url = api_url + '/item/%s/%s' % (namespace, nid)
        resp = requests.post(get_tiid_url)
        
        tiid = json.loads(resp.text)
        #print tiid
        tiid_list = tiid_list + [tiid]
    
    #print "returning tiid list."
    return tiid_list
    
    
def create_collection(tiids, collection_num=1):
    url = api_url+"/collection"
    resp = requests.post(
        url,
        data=json.dumps(
            {
                "items": tiids, 
                "title":"My Collection number " + str(collection_num)
            }
        ),
        headers={'Content-type': 'application/json'}
    )
    collection_id = json.loads(resp.text)["id"]
    #print "returning collection id: " + collection_id
    return collection_id
    
def poll_collection_tiids(collection_id):
    resp = requests.get(api_url + "/collection/"+collection_id)
    tiids = json.loads(resp.text)["item_tiids"]
    tiids_str = ",".join(tiids)
    still_updating = True
    tries = 0
    while still_updating:
        url = api_url+"/items/"+tiids_str
        #print url
        resp = requests.get(url, config={'verbose': None})
        items = json.loads(resp.text)
        #print items
        currently_updating_flags = [True for item in items if item["currently_updating"]]
        num_currently_updating = len(currently_updating_flags)
        num_finished_updating = len(tiids) - num_currently_updating
        sys.stdout.write("\rfinished: %i of %i, get request count %i" % (num_finished_updating, len(tiids), tries))
        sys.stdout.flush()
        #print resp.text
        #print resp.status_code
        if resp.status_code == 200:
            still_updating = False
        
        sleep(0.5)
        tries += 1
    

def test_one_user(collection_size):
    ids = id_list[0:collection_size]
    #print ids
    tiids = create_items(ids)
    collection_id = create_collection(tiids)
    poll_collection_tiids(collection_id)
    
def run_test(collection_size):
    #print "starting test..."
    print "\n\nStarting test: collection size of %i" %collection_size
    mydao = dao.Dao(base_db_url, base_db)
    mydao.delete_db(base_db)
    mydao.create_db(base_db)
    start_time = time.time()
    test_one_user(collection_size)
    elapsed_time = time.time() - start_time
    print "\nFinished test: collection size of %i took %0.1f seconds" %(collection_size, elapsed_time)

run_test(1)
#run_test(2)
#run_test(5)
#run_test(10)
#run_test(25)
#run_test(50)
#run_test(100)


