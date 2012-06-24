import os, requests, json, couchdb
from time import sleep

#kill the database
base_url = "http://total-impact-core-staging.herokuapp.com"
id_list = [("doi", "10.1371/journal.pone.00" + str(x)) for x in range(2900, 3900)]



def create_items(ids):
    ## Get all the tiids
    tiid_list = []
    for (namespace, nid) in ids:
        get_tiid_url = base_url + '/item/%s/%s' % (namespace, nid)
        resp = requests.post(get_tiid_url)
        
        tiid = json.loads(resp.text)
        tiid_list = tiid_list + [tiid]
    
    print "returning tiid list."
    return tiid_list
    
    
def create_collection(tiids, collection_num=1):
    url = base_url+"/collection"
    resp = requests.post(
        url,
        data=json.dumps(
            {
                "items": tiids, 
                "title":"My Collection number " + str(collection_num)
            }
        ),
        content_type="application/json"
    )
    print "returning collection id: " + resp.text
    return resp.text[1:-1] #remove quotes
    
def poll_collection_tiids(collection_id):
    resp = requests.get(base_url+"/collection/"+collection_ids)
    tiids = json.loads(resp.text)
    tiids_str = ",".join(tiids)
    still_updating = True
    while still_updating:
        print "running update."
        url = base_url+"/items/"+tiids_str
        requests.get(url)
        if resp.status_code == 200:
            still_updating = False
        
        sleep(.5)
    

def test_one_user(collection_size):
    ids = id_list[0:collection_size]
    print ids
    tiids = create_items(ids)
#    collection_id = create_collection(tiids)
#    poll_collection_tiids(collection_id)
    

print "starting test..."
test_one_user(1)