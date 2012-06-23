
#kill the database
base_url = 'http://localhost:5001/'
id_list = list of 1000 identiers
number_of_collections = 5

## Get all the tiids
tiid_list = []
for (namespace, nid) in id_list:
	get_tiid_url = base_url + 'item/%s/%s' % (namespace, nid)
    get_tiid_req = urllib2.Request(get_tiid_url)
    data = "" #blank data to force a post
    get_tiid_response = urllib2.urlopen(get_tiid_req, data)

    tiid = json.loads(urllib.unquote(get_tiid_response.read()))
    tiid_list += [tiid]

## make all the collections
collection_ids_list = []
for i in range(1, number_of_collections):
	size_of_collection = len(tiid_list)/number_of_collections
	first_item_index = i*size_of_collection
	tiids_in_this_collection = tiid_list[first_item_index:(first_item_index+size_of_collection)]
    response = self.client.post(
        '/collection',
        data=json.dumps({"items": tiids_in_this_collection, "title":"My Collection number " + str(i)}),
        content_type="application/json")

    assert_equals(response.status_code, 201)  #Created

    response_loaded = json.loads(response.data)
    new_collection_id = response_loaded["id"]
    collection_ids_list += [new_collection_id]

## get all the collections
for collection_id in collection_ids_list:
    get_collection_url = base_url + 'collection/%s' % (collection_id)
    get_collection_request = urllib2.Request(get_collection_url)
    get_collection_response = urllib2.urlopen(get_collection_request)
    assert(get_collection_response.status_code == 200)

## give it a few seconds
sleep(5)

## see if all the metrics are ready
for tiid in tiid_list:
    get_metrics_url = base_url + 'item/%s' % (tiid)
    get_metrics_request = urllib2.Request(get_metrics_url)
    get_metrics_response = urllib2.urlopen(get_metrics_request)

    assert(get_metrics_response.status_code == 200)


