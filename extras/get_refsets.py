import random_pmids
import requests
import os
import json
import re
import random

def get_random_dryad_dois(year, sample_size, seed):
    if year < 2009:
        return []

    url = "http://datadryad.org/solr/search/select/?q=location:l2+dc.date.available_dt:[{year}-01-01T00:00:00Z%20TO%20{year}-12-31T23:59:59Z]&fl=dc.identifier&rows=1000000".format(year=year)
    try:
        r = requests.get(url, timeout=10)
    except requests.Timeout:
        print "dryad isn't working right now (timed out); sending back an empty list."
        return []
    # sick of parsing xml to get simple things.  I'm using regex this time, darn it.
    all_dois = re.findall("<str>doi:(10.5061/dryad.\d+)</str>", r.text)

    if seed:
        random.seed(seed)
    random_dois = random.sample(all_dois, sample_size)
    return random_dois

def get_random_crossref_dois(year, sample_size):
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
    print collection_id
    return collection_id

def collection_metadata(genre, refset_name, year, seed, sample_size):
    refset_metadata = {
        "genre": genre, 
        "version": 0.1,
        "name": refset_name, 
        "year": year, 
        "seed": seed,
        "sample_size": sample_size
    }  
    return refset_metadata

def build_collections_from_eutils(query_template, title_template, year, sample_size, seed):
    collection_ids = []
    for refset_name in query_template:
        print refset_name
        query = query_template[refset_name].format(year=year)
        pmids = random_pmids.get_random_pmids(sample_size, email, query, seed)
        if pmids:
            print pmids
            refset_metadata = collection_metadata("article", refset_name, year, seed, sample_size)
            title = title_template.format(**refset_metadata)
            collection_id = make_collection("pmid", pmids, title, refset_metadata)
            print collection_id
            collection_ids.append(collection_id)
    return collection_ids


def build_collections_from_crossref(query_template, title_template, year, sample_size, seed):
    refset_name = "crossref"
    print refset_name
    dois = get_random_crossref_dois(year, sample_size)
    collection_ids = []
    if dois:
        print dois
        refset_metadata = collection_metadata("article", refset_name, year, "", sample_size)
        title = title_template.format(**refset_metadata)
        collection_id = make_collection("doi", dois, title, refset_metadata)
        collection_ids.append(collection_id)
    return collection_ids

def build_collections_from_dryad(query_template, title_template, year, sample_size, seed):
    refset_name = "dryad"
    print refset_name
    dois = get_random_dryad_dois(year, sample_size, seed)
    collection_ids = []
    if dois:
        print dois
        refset_metadata = collection_metadata("dataset", refset_name, year, seed, sample_size)
        title = title_template.format(**refset_metadata)
        collection_id = make_collection("doi", dois, title, refset_metadata)
        collection_ids.append(collection_id)        
    return collection_ids

def build_reference_sets(query_templates, title_template, years, sample_size, seed):
    collection_ids = []
    for year in years:
        print year
        #collection_ids += build_collections_from_eutils(query_templates["eutils"], title_template, year, sample_size, seed)
        #collection_ids += build_collections_from_crossref(query_templates["random_crossref_doi"], title_template, year, sample_size, seed)
        collection_ids += build_collections_from_dryad(query_templates["random_dryad_doi"], title_template, year, sample_size, seed)
    return(collection_ids)


# export API_ROOT=total-impact-core.herokuapp.com
# export API_ROOT=total-impact-core-staging.herokuapp.com

#Useful references for queries:
#http://www.nlm.nih.gov/bsd/funding_support.html
#http://www.nlm.nih.gov/bsd/grant_acronym.html#pub_health
query_templates = {
    "eutils": {
        #'pubmed':   'Journal Article[pt] AND {year}[dp]',
        #'nih':          "(Research Support, U.S. Gov't, P.H.S. [pt] OR nih [gr]) AND Journal Article[pt] AND {year}[dp]",
        'plosone':      '"plos one"[journal] AND Journal Article[pt] AND {year}[dp]',
        'nature':       '"nature"[journal] AND Journal Article[pt] AND {year}[dp]',
        #'science':      '"science"[journal] AND Journal Article[pt] AND {year}[dp]',
        },
    "random_crossref_doi":{
        'dois': None
        },
    "random_dryad_doi":{
        'dois': None
        }
    }

sample_size = 100
seed = 42
years = range(2001, 2012)
title_template = "REFSET {name}, {year} ({genre}) n={sample_size}"
email = "team@total-impact.org"
api_url = "http://" + os.getenv("API_ROOT")

collection_ids = build_reference_sets(query_templates, title_template, years, sample_size, seed)
for collection_id in collection_ids:
    print collection_id



