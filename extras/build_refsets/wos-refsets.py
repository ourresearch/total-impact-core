import re
import random
import json
import requests

# from get_refsets.py
def make_collection(api_url, namespace, nids, title, refset_metadata):
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

# cat */*.bib > all.bib
#filename = "/Users/hpiwowar/Dropbox/ti/wos-refset/all.bib"
filename = "/Users/hpiwowar/Dropbox/ti/wos-refset/2012/all2012.bib"
contents = open(filename, "r").read()
doi_pattern = re.compile("DOI = {{(.+)}},")
all_dois = doi_pattern.findall(contents)

year_pattern = re.compile("Year = {{(.+)}}")
all_years = year_pattern.findall(contents)

doi_years = zip(all_dois, all_years)

title_template = "REFSET {name}, {year} ({genre}) n={sample_size}"
#api_url = "http://total-impact-core-staging.herokuapp.com"
api_url = "http://total-impact-core.herokuapp.com"

for refset_year in range(2012, 2013):
    print refset_year
    dois = [doi for (doi, year) in doi_years if year==unicode(refset_year)]
    print len(dois)
    seed = 42
    random.seed(seed)
    sample_size = 100
    selected = random.sample(dois, min(sample_size, len(dois)))
    refset_metadata = {
        "genre": "article", 
        "version": 0.1,
        "name": "WoS",
        "year": refset_year, 
        "seed": seed,
        "sample_size": sample_size
    }
    title = title_template.format(**refset_metadata)
    collection_id = make_collection(api_url, "doi", selected, title, refset_metadata)
    print collection_id

