import random_pmids
import requests
import os
import json
import re
import random

def get_nth_figshare_id(url_template, year, n):
    (page_minus_one, offset) = divmod(n, 10)  #figshare api always has 10 things on a page
    url = url_template.format(page=page_minus_one+1, year=year)
    print url
    r = requests.get(url, timeout=10)    
    response = json.loads(r.text)
    try:
        items = response["items"]
        item = items[offset]
        doi = item["DOI"]
        year_of_item = item["published_date"][-4:]
    except (AttributeError):
        print "no doi found ", item
        doi = None
    except KeyError:
        print response
        # try the next page, as a workaround
        return get_nth_figshare_id(url_template, year, n+10)

    doi = doi.replace("http://dx.doi.org/", "")
    return({"doi":doi, "year":year_of_item})

def get_random_figshare_dois(year, sample_size, email, query, seed=None):
    if year < 2011:
        return []

    url_template = "http://api.figshare.com/v1/articles/search?search_for=*&from_date={year}-01-01&to_date={year}-12-31&page={page}&has_publisher_id=0"

    # Do an initial query to get the total number of hits
    url = url_template.format(page=1, year=year)
    print url
    r = requests.get(url)
    initial_response = json.loads(r.text)
    print initial_response
    population_size = initial_response["items_found"]
    print "Number of figshare items returned by this query: %i" %population_size
    print "Off to randomly sample %i of them!" %sample_size

    if seed:
        random.seed(seed)
        print "Seed has been set before sampling."

    if sample_size > population_size:
        print "sample size is bigger than population size, so using population size"
        sample_size = population_size
    random_indexes = random.sample(range(1, population_size), sample_size)

    figshare_ids = []
    for random_index in random_indexes:
        figshare_dict = get_nth_figshare_id(url_template, year, random_index)
        doi = figshare_dict["doi"]
        print "figshare_id:" + doi
        figshare_ids.append(doi)
    return figshare_ids


def get_random_dryad_dois(year, sample_size, email, query, seed=None):
    if year < 2009:
        return []

    url = "http://datadryad.org/solr/search/select/?q=location:l2+dc.date.available_dt:[{year}-01-01T00:00:00Z%20TO%20{year}-12-31T23:59:59Z]&fl=dc.identifier&rows=1000000".format(year=year)
    print url
    try:
        r = requests.get(url, timeout=10)
    except requests.Timeout:
        print "dryad isn't working right now (timed out); sending back an empty list."
        return []
    # sick of parsing xml to get simple things.  I'm using regex this time, darn it.
    all_dois = re.findall("<str>doi:(10.5061/dryad.[a-z0-9]+)</str>", r.text)
    print all_dois[1]
    print len(all_dois)

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

def get_random_github_dict():
    from totalimpact.providers import github
    # downloaded from http://archive.org/details/archiveteam-github-repository-index-201212
    filename = "/Users/hpiwowar/Documents/Projects/tiv2/total-impact-core/extras/build_refsets/github-repositories.txt"

    import collections
    import subprocess
    command = "wc " + filename
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, error = p.communicate()
    num_repos = int(out.strip().split(" ")[0])
    print num_repos
    seed = 42
    random.seed(seed)

    provider = github.Github()

    random_repos = collections.defaultdict(list)

    i = 0
    while (len(random_repos["2009"]) < 100):
        i += 1
        line_number = random.randint(0, num_repos)
        command = "tail -n +{line_number} {filename} | head -n 1".format(
            line_number=line_number, filename=filename)
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        repo_id, error = p.communicate()
        print repo_id
        repo_url = "https://github.com/" + repo_id.strip()
        biblio = provider.biblio([("url", repo_url)])
        try:
            year = biblio["create_date"][0:4]
        except KeyError:
            continue
        random_repos[year] += [repo_url]
        print "\nn={number_sampled}".format(number_sampled=i)
        for year in sorted(random_repos.keys()):
            print "{year}: {num}".format(year=year, num=len(random_repos[year]))
        if i%100 == 0:
            print random_repos
    print random_repos
    return random_repos

def get_random_github_ids(year, sample_size, email, query, seed):
    if year < 2009:
        return []

    filename = "/Users/hpiwowar/Documents/Projects/tiv2/total-impact-core/extras/build_refsets/random_github_repos.py"
    from random_github_repos import random_github_repos

    if seed:
        random.seed(seed)
    random_ids = random.sample(random_github_repos[str(year)], sample_size)
    return random_ids


def make_collection(namespace, nids, title, refset_metadata):
    aliases = [(namespace, nid) for nid in nids]
    url = api_url + "/v1/collection?key=" + os.getenv("API_KEY")
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


def build_collections(refset_name, get_random_ids_func, genre, namespace, query_template, title_template, year, sample_size, seed):
    collection_ids = []
    print refset_name
    if query_template:
        query = query_template[refset_name].format(year=year)
    else:
        query = None
    ids = get_random_ids_func(year, sample_size, email, query, seed)
    if ids:
        print ids
        refset_metadata = collection_metadata(genre, refset_name, year, seed, sample_size)
        title = title_template.format(**refset_metadata)
        collection_id = make_collection(namespace, ids, title, refset_metadata)
        print collection_id
        collection_ids.append(collection_id)
    return collection_ids



def build_reference_sets(refset_name, query_templates, title_template, years, sample_size, seed):
    collection_ids = []
    for year in years:
        print year
        if refset_name == "eutils":
            collection_ids += build_collections(refset_name, random_pmids.get_random_pmids, "article", "pmid", query_template, title_template, year, sample_size, seed)
        elif refset_name == "crossref":
            collection_ids += build_collections(refset_name, get_random_crossref_dois, "article", "doi", None, title_template, year, sample_size, "")
        elif refset_name == "dryad":
            collection_ids += build_collections(refset_name, get_random_dryad_dois, "dataset", "doi", None, title_template, year, sample_size, seed)
        elif refset_name == "figshare":
            collection_ids += build_collections(refset_name, get_random_figshare_dois, "dataset", "doi", None, title_template, year, sample_size, seed)
        elif refset_name == "github":
            collection_ids += build_collections(refset_name, get_random_github_ids, "software", "url", None, title_template, year, sample_size, seed)
    return(collection_ids)

#Useful references for queries:
#http://www.nlm.nih.gov/bsd/funding_support.html
#http://www.nlm.nih.gov/bsd/grant_acronym.html#pub_health
query_templates = {
    #"eutils": {
        #'pubmed':   'Journal Article[pt] AND {year}[dp]',
        #'nih':          "(Research Support, U.S. Gov't, P.H.S. [pt] OR nih [gr]) AND Journal Article[pt] AND {year}[dp]",
        #'plosone':      '"plos one"[journal] AND Journal Article[pt] AND {year}[dp]',
        #'nature':       '"nature"[journal] AND Journal Article[pt] AND {year}[dp]',
        #'science':      '"science"[journal] AND Journal Article[pt] AND {year}[dp]',
    #    },
    }


title_template = "REFSET {name}, {year} ({genre}) n={sample_size}"
email = "team@impactstory.org"
# export API_ROOT=total-impact-core.herokuapp.com
# export API_ROOT=total-impact-core-staging.herokuapp.com
# api_url = "http://" + os.getenv("API_ROOT")
api_url = "http://total-impact-core-staging.herokuapp.com"

sample_size = 100
seed = 42
years = range(2013, 2014)
refset_name = "dryad"

collection_ids = build_reference_sets(refset_name, query_templates, title_template, years, sample_size, seed)
for collection_id in collection_ids:
    print collection_id

