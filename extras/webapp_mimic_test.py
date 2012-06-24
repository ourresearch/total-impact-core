import os, requests, json, couchdb, time
from time import sleep

#kill the database.  
# Don't get db from env variable because don't want to kill production by mistake
#base_url = "http://total-impact-core-staging.herokuapp.com"

api_url = "http://localhost:5001"

base_db_url = "http://localhost:5984"
base_db = "localdb"

id_list = [("doi", "10.1371/journal.pone.000" + str(x)) for x in range(2901, 3901)]

def delete_db():
	server = couchdb.Server(base_db_url)
	del server[base_db]

def create_items(ids):
    ## Get all the tiids
    tiid_list = []
    for (namespace, nid) in ids:
        get_tiid_url = api_url + '/item/%s/%s' % (namespace, nid)
        resp = requests.post(get_tiid_url)
        
        tiid = json.loads(resp.text)
        #print tiid
        tiid_list = tiid_list + [tiid]
    
    print "returning tiid list."
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
    print "returning collection id: " + collection_id
    return collection_id
    
def poll_collection_tiids(collection_id):
    resp = requests.get(api_url + "/collection/"+collection_id)
    tiids = json.loads(resp.text)["item_tiids"]
    tiids_str = ",".join(tiids)
    still_updating = True
    while still_updating:
        print "running update."
        url = api_url+"/items/"+tiids_str
        #print url
        resp = requests.get(url)
        #print resp.text
        print resp.status_code
        if resp.status_code == 200:
            still_updating = False
        
        sleep(0.5)
    

def test_one_user(collection_size):
    ids = id_list[0:collection_size]
    #print ids
    tiids = create_items(ids)
    collection_id = create_collection(tiids)
    poll_collection_tiids(collection_id)
    
def run_test(collection_size):
	print "starting test..."
	print "colleciton size %i" %collection_size
	#delete_db()
	start_time = time.time()
	test_one_user(collection_size)
	elapsed_time = time.time() - start_time
	print elapsed_time

run_test(1)
run_test(10)
run_test(100)


