#!/usr/bin/env python
#
# A basic functional test of the total impact API
#

import urllib2
import urllib
import json
import time
import sys
import pickle
from pprint import pprint
from optparse import OptionParser

TEST_ITEMS = {
    ('doi', '10.1371/journal.pcbi.1000361') :
        { 
            'aliases': ['doi', "title", "url"],
            'biblio': [u'authors', u'journal', u'year', u'title'],
            'metrics' : {
                'wikipedia:mentions' : 1,
                u'plosalm:crossref': 133,
                 'plosalm:html_views': 17455,
                 'plosalm:pdf_views': 2106,
                 u'plosalm:pmc_abstract': 19,
                 u'plosalm:pmc_figure': 71,
                 u'plosalm:pmc_full-text': 1092,
                 u'plosalm:pmc_pdf': 419,
                 u'plosalm:pmc_supp-data': 157,
                 u'plosalm:pmc_unique-ip': 963,
                 u'plosalm:pubmed_central': 102,
                 u'plosalm:scopus': 218
            }
        },
    ('url', 'http://total-impact.org/') : #note trailing slash
        { 
            'aliases': ["url"],
            'biblio': ['title'],
            'metrics' : {
                'delicious:bookmarks' : 65
            }
        },
    ('url', 'http://total-impact.org'): #no trailing slash
        { 
            'aliases': ["url"],
            'biblio': ['title'],
            'metrics' : {
                'topsy:tweets' : 282,
                'topsy:influential_tweets' : 26
            }
        },                    
    ('doi', '10.5061/dryad.18') : 
        { 
            'aliases': ['doi', 'url', 'title'],
            'biblio': [u'authors', u'year', u'repository', u'title'],
            'metrics' : {
                'dryad:most_downloaded_file' : 63,
                'dryad:package_views' : 149,
                'dryad:total_downloads' : 169
            }
        },
    ('github', 'egonw,cdk') :
        { 
            'aliases': ['github', 'url', 'title'],
            'biblio': [u'last_push_date', u'create_date', u'description', u'title', u'url', u'owner', 'h1'],
            'metrics' : {
                'github:forks' : 27,
                'github:watchers' : 31
            }
        },                    
    ('url', 'http://nescent.org/'):
        { 
            'aliases': ['url'],
            'biblio': [u'title', "h1"],
            'metrics' : {}
        },
    ('url', 'http://www.slideshare.net/cavlec/manufacturing-serendipity-12176916') :
        {
            'aliases' : ['url', 'title'],
            'biblio': [u'username', u'repository', u'created', u'h1', u'genre', u'title'],
            'metrics' : {
                'slideshare:downloads' : 4,
                'slideshare:views' : 337,
                'slideshare:favorites' : 2
            }
        }
}

class TotalImpactAPI:
    base_url = 'http://localhost:5001/'

    def request_item(self, alias):
        """ Attempt to obtain an item from the server using the given
            namespace and namespace id. For example, 
              namespace = 'pubmed', nid = '234234232'
            Will request the item related to pubmed item 234234232
        """

        (namespace, nid) = alias
        url = self.base_url + urllib.quote('item/%s/%s' % (namespace, nid))
        req = urllib2.Request(url)
        data = {} # fake a POST
        response = urllib2.urlopen(req, data)
        tiid = json.loads(urllib.unquote(response.read()))
        print "tiid %s for %s" %(tiid, alias)
        return tiid

    def request_item_result(self, item_id):
        url = self.base_url + urllib.quote('item/%s' % (item_id))
        req = urllib2.Request(url)
        response = urllib2.urlopen(req)
        return json.loads(response.read())
        

def checkItem(item, data, alias, items_for_use, options):
    if options.debug: 
        print "Checking %s result (%s)..." % (alias, item)
    
    success = True
    for section in ["biblio", "aliases", "metrics"]:
        result = checkItemSection(alias, 
                item, 
                section, 
                data[section], 
                items_for_use[alias], 
                options)
        if not result:
            success = False
    return success

def checkItemSection(alias, id, section, api_response, gold_item, options):
    success = True
    if options.debug:
        print "Checking %s result (%s)..." % (alias, id)

    # Check aliases are correct
    if section=="aliases":
        gold_aliases = gold_item['aliases']
        alias_result = set(api_response.keys())
        expected_result = set(gold_aliases + [u'last_modified', u'created'])
        if (alias_result == expected_result):
            if options.debug:
                print "ALIASES CORRECT! %s" %(alias_result)
        else:
            if options.debug:
                print "ALIASES **NOT** CORRECT, for %s, %s, have %s, want %s" %(alias, id, alias_result, expected_result)
            success = False

    # Check biblio are correct
    elif section=="biblio":
        gold_biblio = gold_item['biblio']    
        if api_response:
            biblio_result = set(api_response.keys())
        else:
            biblio_result = set([])
        expected_result = set(gold_biblio + ['genre'])

        if (biblio_result == expected_result):
            if options.debug:
                print "BIBLIO CORRECT! %s" %(biblio_result)
        else:
            if options.debug:
                print "BIBLIO **NOT** CORRECT, have %s, want %s" %(biblio_result, expected_result)
            success = False

    # Check we've got some metric values
    elif section=="metrics":
        gold_metrics = gold_item['metrics']
        for metric in gold_metrics.keys():
            try:
                metric_data = api_response[metric].values()[0]
            except KeyError:
                # didn't return anything.  problem!
                if options.debug:
                    print "METRICS **NOT** CORRECT for %s: metric missing" % (metric)
                success = False

            # expect the returned value to be equal or larger than reference
            if success:
                if metric_data >= gold_metrics:
                    if options.debug:
                        print "METRICS CORRECT! %s" %(metric_data)
                else:
                    if options.debug:
                        print "METRICS **NOT** CORRECT for %s - %s, expected at least %s" % (metric, metric_data, gold_metrics)
                    return False

    if options.debug:
        print #blank line

    return success




if __name__ == '__main__':


    parser = OptionParser()
    parser.add_option("-n", "--numrepeats", dest="numrepeats", 
            default=1, help="Number of repeated requests to make")
    parser.add_option("-i", "--items", dest="numdiverseitems", 
            default=999, 
            help="Number of diverse items to use (up to max defined)")
    parser.add_option("-m", "--missing", dest="missing", 
            default=False, action="store_true", 
            help="Display any outstanding items")
    parser.add_option("-p", "--printdata", dest="printdata", 
            default=False, action="store_true", help="Display item data")
    parser.add_option("-v", "--verbose", dest="debug", 
            default=False, action="store_true", help="Display verbose debug data")
    (options, args) = parser.parse_args()


    item_count = int(options.numrepeats)
    num_diverse_items = min(len(TEST_ITEMS), int(options.numdiverseitems))
    aliases = TEST_ITEMS.keys()[0:num_diverse_items]
    items_for_use = dict((alias, TEST_ITEMS[alias]) for alias in aliases)
    
    ti = TotalImpactAPI()

    complete = {}
    itemid = {}



    for alias in aliases:
        complete[alias] = {}
        itemid[alias] = {}
        for idx in range(item_count):
            # Request the items to be generated
            itemid[alias][idx] = ti.request_item(alias)
            complete[alias][idx] = False

    while True:
        for idx in range(item_count):
            for alias in aliases:
                if not complete[alias][idx]:
                    if options.missing:
                        print alias, idx, itemid[alias][idx]
                    
                    itemdata = ti.request_item_result(itemid[alias][idx])

                    complete[alias][idx] = checkItem(
                        itemid[alias][idx], 
                        itemdata,
                        alias, 
                        items_for_use,
                        options
                    )
                    if complete[alias][idx] and options.printdata:
                        pprint(itemdata)

        total = sum([sum(complete[alias].values()) for alias in aliases])
        print "%i of %i responses are complete" %(total, item_count * len(aliases))
        if total == item_count * len(aliases):
            sys.exit(0)    

        time.sleep(0.5)

