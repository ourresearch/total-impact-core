import random_pmids
import requests
import os
import json


def get_random_dois(year, sample_size):
    url = "http://random.labs.crossref.org/dois?from=2000&count=n" + str(sample_size)
    try:
        r = requests.get(url, timeout=10)
    except requests.Timeout:
        print "the random doi service isn't working right now (timed out); sending back an empty list."
        return []
    dois = json.loads(r.text)
    return dois

def make_collection(namespace, nids, title, refset_metadata):
    aliases = [(namespace, nid) for nid in nids]
    url = api_url + "/collection"
    resp = requests.post(
        url,
        data=json.dumps({
            "aliases": aliases,
            "title": title,
            "refset_metadata": refset_metadata
        }),
        headers={'Content-type': 'application/json'}
    )
    collection_id = json.loads(resp.text)["collection"]["_id"]
    return collection_id

def build_reference_sets(query_templates, years, sample_size, seed):
    collection_ids = []
    for refset_name in query_templates["eutils"]:
        print refset_name
        for year in years:
            print year
            query = query_templates["eutils"][refset_name].format(year=year)
            pmids = random_pmids.get_random_pmids(sample_size, email, query, seed)
            if pmids:
                print pmids
                refset_metadata = {
                    "genre":"article", 
                    "version":0.1,
                    "name":refset_name, 
                    "year":year, 
                    "seed":seed,
                    "sample_size":sample_size
                }                
                title = title_template.format(**refset_metadata)
                collection_id = make_collection("pmid", pmids, title, refset_metadata)
                print collection_id
                collection_ids.append(collection_id)
    for refset_name in query_templates["random_doi"]:
        print refset_name
        for year in years:
            dois = get_random_dois(year, sample_size)
            if dois:
                print dois
                refset_metadata = {
                    "genre":"article", 
                    "version":0.1,
                    "name":refset_name, 
                    "year":year, 
                    "seed":"",
                    "sample_size":sample_size
                }
                title = title_template.format(**refset_metadata)
                collection_id = make_collection("doi", dois, title, refset_metadata)
                collection_ids.append(collection_id)
    return(collection_ids)


#Useful references for queries:
#http://www.nlm.nih.gov/bsd/funding_support.html
#http://www.nlm.nih.gov/bsd/grant_acronym.html#pub_health
query_templates = {
    "eutils": {
        #'pubmed':   'Journal Article[pt] AND {year}[dp]',
        #'nih':          "(Research Support, U.S. Gov't, P.H.S. [pt] OR nih [gr]) AND Journal Article[pt] AND {year}[dp]",
        #'plosone':      '"plos one"[journal] AND Journal Article[pt] AND {year}[dp]',
        #'nature':       '"nature"[journal] AND Journal Article[pt] AND {year}[dp]',
        #'science':      '"science"[journal] AND Journal Article[pt] AND {year}[dp]',
        },
    "random_doi":{
        'dois': None
        }
    }


sample_size = 100
seed = 42
years = range(2001, 2012)
title_template = "REFSET {genre}: {name} {year}. n={sample_size}, seed={seed}"
email = "team@total-impact.org"
api_url = "http://" + os.getenv("API_ROOT")

build_reference_sets(query_templates, years, sample_size, seed)

