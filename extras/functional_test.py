#!/usr/bin/env python
#
# A basic functional test of the total impact API
#

import mechanize
import urllib2
import urllib
import json
import time
import sys
import pickle
from pprint import pprint

request_ids = {"dryad": ('doi','10.5061/dryad.7898'), 
                "wikipedia": ('doi', '10.1371/journal.pcbi.1000361'), 
                "github": ('github', 'egonw/gtd')}

class TotalImpactAPI:
    base_url = 'http://localhost:5001/'

    def request_item(self, namespace, nid):
        """ Attempt to obtain an item from the server using the given
            namespace and namespace id. For example, 
              namespace = 'pubmed', nid = '234234232'
            Will request the item related to pubmed item 234234232
        """

        url = self.base_url + urllib.quote('item/%s/%s' % (namespace, nid))
        print url
        req = urllib2.Request(url)
        data = {} # fake a POST
        response = urllib2.urlopen(req, data)
        tiid = json.loads(urllib.unquote(response.read()))
        return tiid

    def request_item_result(self, tiid):
        url = self.base_url + urllib.quote('item/%s' % (tiid))
        req = urllib2.Request(url)
        response = urllib2.urlopen(req)
        return json.loads(response.read())
        

from optparse import OptionParser


def checkItem(tiid, api_response, provider, debug=False):
    checks = {
        'wikipedia' : { 
            'aliases': ['doi'],
            'biblio': [],
            'metrics' : {
                'wikipedia:mentions' : 1
            }
        },
        'github' : { 
            'aliases': ['github', 'url', 'title'],
            'biblio': [u'last_push_date', u'create_date', u'description', u'title', u'url', u'owner'],
            'metrics' : {
                'github:forks' : 0,
                'github:watchers' : 7
            }
        },
        'dryad' : { 
            'aliases': ['doi', 'url', 'title'],
            'biblio': ['title', 'year'],
            'metrics' : {
                'dryad:most_downloaded_file' : 63,
                'dryad:package_views' : 149,
                'dryad:total_downloads' : 169
            }
        }
    }

    aliases = checks[provider]['aliases']
    metrics = checks[provider]['metrics']
    biblio = checks[provider]['biblio']

    if debug: print "Checking %s result (%s)..." % (provider, tiid)
    
    # Check aliases are correct
    alias_result = set(api_response['aliases'].keys())
    expected_result = set(aliases + 
        ['created','last_modified','last_completed'])
    if alias_result != expected_result:
        if debug: 
            print "Aliases is not correct, have %s, want %s" %(alias_result, expected_result)
        return False

    # Check biblio are correct
    if api_response['biblio']:
        biblio_result = set(api_response['biblio']['data'].keys())
    else:
        biblio_result = set([])
    expected_result = set(biblio)

    if biblio_result != expected_result:
        if debug: 
            print "Biblio is not correct, have %s, want %s" %(biblio_result, expected_result)
        return False

    # Check we've got some metric values
    for metric in metrics.keys():
        metric_data = api_response['metrics'][metric]['values']
        if len(metric_data) != 1:
            if debug: 
                print "Incorrect number of metric results for %s - %i" % (metric, len(metric_data))
                print api_response['metrics']
            return False
        else:
            # expect the returned value to be equal or larger than reference
            if metric_data.values()[0] < metrics[metric]:
                if debug: 
                    print "Incorrect metric result for %s - %s, expected at least %s" % (metric, metric_data.values()[0], metrics[metric])
                print api_response['metrics']                    
                return False

    return True




if __name__ == '__main__':

    parser = OptionParser()
    parser.add_option("-s", "--simultaneous", dest="simultaneous", default=1,
                      help="Number of simultaneous requests to make")
    parser.add_option("-m", "--missing", dest="missing", default=False, action="store_true",
                      help="Display any outstanding items")
    parser.add_option("-p", "--printdata", dest="printdata", default=False, action="store_true",
                      help="Display item data")
    (options, args) = parser.parse_args()


    item_count = int(options.simultaneous)
    
    ti = TotalImpactAPI()

    dryad_item = wikipedia_item = github_item = []
    dryad_data = wikipedia_data = github_data = []
    complete = {}
    tiids = {}
    final_responses = {}
    providers = request_ids.keys()

    for provider in providers:
        complete[provider] = {}
        tiids[provider] = {}
        final_responses[provider] = {}

    for idx in range(item_count):
        # Request the items to be generated
        for provider in providers:
            (namespace, nid) = request_ids[provider]
            tiids[provider][idx] = ti.request_item(namespace, nid)

    for idx in range(item_count):
        for provider in providers:
            (namespace, nid) = request_ids[provider]
            tiids[provider][idx] = ti.request_item(namespace, nid)
            complete[provider][idx] = False

    while True:

        for idx in range(item_count):
            for provider in providers:
                if not complete[provider][idx]:
                    tiid = tiids[provider][idx]
                    if options.missing:
<<<<<<< HEAD
                        print item_type, idx, itemid[item_type][idx]
                    
                    itemdata = ti.request_item_result(itemid[item_type][idx])
                    complete[item_type][idx] = checkItem(
                        itemid[item_type][idx], itemdata,
                        item_type, debug=options.missing
=======
                        print provider, idx, tiid
                    api_response = ti.request_item_result(tiid)
                    final_responses[provider][idx] = api_response
                    complete[provider][idx] = checkItem(
                        tiid,
                        api_response,
                        provider, 
                        debug=options.missing
>>>>>>> functional_tests use sample_provider_pages for dryad
                    )
                    if complete[item_type][idx] and options.printdata:
                        pprint(itemdata)


        total = sum([sum(complete[provider].values()) for provider in providers])
        print [(provider, sum(complete[provider].values())) for provider in providers], total
        if total == item_count * len(providers):
            print tiids
            pprint(final_responses)
            sys.exit(0)    

        time.sleep(0.5)

