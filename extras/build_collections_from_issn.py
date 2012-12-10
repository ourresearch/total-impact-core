import requests, os, json, time
from totalimpact.updater import active_publishers

def make_collection(namespace, nids, title, api_url):
    aliases = [(namespace, nid) for nid in nids]
    url = api_url + "/v1/collection?key=Heather"
    data_payload = json.dumps({
            "aliases": aliases,
            "title": title
        })
    resp = requests.post(url, data=data_payload, headers={'Content-type': 'application/json'})
    print resp.status_code
    collection_response = resp.json
    collection_id = collection_response["collection"]["_id"]
    print collection_id
    return collection_id

def get_all_crossref_dois_for_an_issn(issn):
    crossref_api_page_number = 1
    crossref_api_page_size = 100
    dois = []
    while crossref_api_page_number:
        print("page {crossref_api_page_number}".format(
            issn=issn, crossref_api_page_number=crossref_api_page_number))
        url = "http://search.labs.crossref.org/dois?q={issn}&rows={page_size}&page={page}&header=true".format(
            issn=issn, page=crossref_api_page_number, page_size=crossref_api_page_size)
        #print url
        try:
            r = requests.get(url, timeout=10)
        except requests.Timeout:
            print "timeout"
            return []
        dois_on_page = [item["doi"] for item in r.json["items"]]
        #print dois_on_page
        dois += dois_on_page
        if crossref_api_page_number*crossref_api_page_size > r.json["totalResults"]:
            crossref_api_page_number = None
        else:
            crossref_api_page_number += 1
    return dois

def create_issn_collections(publishers_dict, title_template, items_per_collection, api_url):
    collection_ids = []
    for publisher in publishers_dict:
        print "\n***", publisher
        for journal in publishers_dict[publisher]["journals"]:
            print "\n", journal
            title = title_template.format(
                issn=journal["issn"], title=journal["title"], publisher=publisher)
            issn_dois = get_all_crossref_dois_for_an_issn(journal["issn"])
            print("got {num} dois".format(
                num = len(issn_dois)))
            if issn_dois:
                dois_in_pages = [issn_dois[i:i+items_per_collection] for i in xrange(0, len(issn_dois), items_per_collection)]
                for dois_for_collection in dois_in_pages:
                    #print dois
                    if True:
                        collection_id = make_collection("doi", dois_for_collection, title, api_url)
                        print title        
                        collection_ids.append(collection_id)
                        print "sleeping to let collection get made slowly\n"
                        time.sleep(30)  #seconds
    return(collection_ids)


# export API_ROOT=total-impact-core.herokuapp.com
# export API_ROOT=total-impact-core-staging.herokuapp.com


#api_url = "http://" + os.getenv("API_ROOT")
api_url = "http://total-impact-core.herokuapp.com"
title_template = "ISSN {issn}: {title}, published by {publisher}"
items_per_collection = 20

collection_ids = create_issn_collections(active_publishers, title_template, items_per_collection, api_url)
for collection_id in collection_ids:
    print collection_id



