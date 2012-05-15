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
                ("mendeley", ('doi', '10.1371/journal.pcbi.1000361')), 
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
    'mendeley' : { 
        'aliases': [u'url', u'doi', u'title'],
        'biblio': [u'authors', u'journal', u'year', u'title'],
        'metrics' : {
            'mendeley:readers' : 50,
            'mendeley:groups' : 4
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
        if debug:
            print("HTTPError on %s %s %s, could be not implemented" % (provider, section, nid))
        result = {}

    return result


def checkItem(provider, id, section, api_response, debug=False):
    if debug: 
        print "Checking %s result (%s)..." % (provider, id)
    
    # Check aliases are correct
    if section=="aliases":
        aliases = GOLD_RESPONSES[provider]['aliases']
        alias_result = set([namespace for (namespace, nid) in api_response])
        expected_result = set(aliases)
        if (alias_result == expected_result):
            if debug: 
                print "Aliases correct! %s" %(alias_result)
        else:
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

        if (biblio_result == expected_result):
            if debug: 
                print "Biblio correct! %s" %(biblio_result)
        else:
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
            else:
                if debug: 
                    print "Metrics correct! %s" %(metric_data)


    return True


def make_call(namespace, nid, provider, options):
    if debug:
        print provider, nid
    for section in ["biblio", "aliases", "metrics"]:
        api_response = request_provider_item(provider, nid, section)
        check_response = checkItem(provider,
            nid, 
            section,
            api_response,
            debug=options.missing
        )
        if check_response and options.printdata:
            pprint(api_response)  


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

    if options.missing:
        debug=True

    for (provider, alias) in REQUEST_IDS:
        print "\r\n****PROVIDER:", provider

        (namespace, nid) = alias
        print "LIVE DATA"
        make_call(namespace, nid, provider, options)

        print "CANNED DATA"
        make_call(namespace, "example", provider, options)
 
        time.sleep(0.5)

