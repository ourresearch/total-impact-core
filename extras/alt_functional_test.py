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
from optparse import OptionParser

REQUEST_IDS = [("dryad", ('doi','10.5061/dryad.18')), 
                ("wikipedia", ('doi', '10.1371/journal.pcbi.1000361')), 
                ("github", ('github', 'egonw,cdk'))
]

GOLD_RESPONSES = {
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


def request_provider_item(provider, nid, section):
    base_url = 'http://localhost:5001/'
    url = base_url + urllib.quote('provider/%s/%s/%s' % (provider, section, nid))
    if debug:
        print url
    req = urllib2.Request(url)
    try:
        response = urllib2.urlopen(req)
        result = json.loads(response.read())
    except urllib2.HTTPError:
        result = []

    return result


def checkItem(provider, id, section, api_response, debug=False):
    if debug: 
        print "Checking %s result (%s)..." % (provider, id)
    
    # Check aliases are correct
    if section=="aliases":
        aliases = GOLD_RESPONSES[provider]['aliases']
        alias_result = set([namespace for (namespace, nid) in api_response])
        expected_result = set(aliases + 
            ['created','last_modified','last_completed'])
        if alias_result != expected_result:
            if debug: 
                print "Aliases is not correct, have %s, want %s" %(alias_result, expected_result)
            return False

    # Check biblio are correct
    elif section=="biblio":
        biblio = GOLD_RESPONSES[provider]['biblio']    
        if api_response:
            biblio_result = set(api_response.keys())
        else:
            biblio_result = set([])
        expected_result = set(biblio)

        if biblio_result != expected_result:
            if debug: 
                print "Biblio is not correct, have %s, want %s" %(biblio_result, expected_result)
            return False

    # Check we've got some metric values
    elif section=="metrics":
        metrics = GOLD_RESPONSES[provider]['metrics']
        for metric in metrics.keys():
            metric_data = api_response[metric]
            # expect the returned value to be equal or larger than reference
            if metric_data < metrics[metric]:
                if debug: 
                    print "Incorrect metric result for %s - %s, expected at least %s" % (metric, metric_data, metrics[metric])
                pprint(api_response)
                return False

    return True




if __name__ == '__main__':
    debug = True

    parser = OptionParser()
    parser.add_option("-s", "--simultaneous", dest="simultaneous", default=1,
                      help="Number of simultaneous requests to make")
    parser.add_option("-m", "--missing", dest="missing", default=False, action="store_true",
                      help="Display any outstanding items")
    parser.add_option("-p", "--printdata", dest="printdata", default=False, action="store_true",
                      help="Display item data")
    (options, args) = parser.parse_args()


    complete = {}
    final_responses = {}

    for (provider, alias) in REQUEST_IDS:
        (namespace, nid) = alias
        complete[provider] = {}
        final_responses[provider] = {}
        complete[provider] = {}
        if options.missing:
            print provider, nid
        for section in ["biblio", "aliases", "metrics"]:
            api_response = request_provider_item(provider, nid, section)
            final_responses[provider][section] = api_response
            complete[provider][section] = checkItem(provider,
                nid, 
                section,
                api_response,
                debug=options.missing
            )
            if complete[provider] and options.printdata:
                pprint(api_response)
 

        time.sleep(0.5)

