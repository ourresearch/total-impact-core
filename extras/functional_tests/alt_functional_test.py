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
import urlparse
from pprint import pprint
from optparse import OptionParser


REQUEST_IDS = [
                ("crossref", ('doi', '10.1371/journal.pcbi.1000361')), 
                ("delicious", ('url', 'http://total-impact.org/')),
                ("dryad", ('doi','10.5061/dryad.18')), 
                ("github", ('github', 'egonw,cdk')),
                ("mendeley", ('doi', '10.1371/journal.pcbi.1000361')), 
                ("topsy", ('url', 'http://total-impact.org')),
                ("webpage", ('url', 'http://nescent.org/')),
                ("wikipedia", ('doi', '10.1371/journal.pcbi.1000361')) 
]

GOLD_RESPONSES = {
    'crossref' : { 
        'aliases': ['doi', "title", "url"],
        'biblio': [u'authors', u'journal', u'year', u'title'],
        'metrics' : {}
    },
    'delicious' : { 
        'aliases': ["url"],
        'biblio': [],
        'metrics' : {
            'delicious:bookmarks' : 65
        }
    },
    'dryad' : { 
        'aliases': ['doi', 'url', 'title'],
        'biblio': [u'authors', u'year', u'repository', u'title'],
        'metrics' : {
            'dryad:most_downloaded_file' : 63,
            'dryad:package_views' : 149,
            'dryad:total_downloads' : 169
        }
    },    
    'github' : { 
        'aliases': ['github', 'url', 'title'],
        'biblio': [u'last_push_date', u'create_date', u'description', u'title', u'url', u'owner'],
        'metrics' : {
            'github:forks' : 27,
            'github:watchers' : 31
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
    'topsy' : { 
        'aliases': ["url"],
        'biblio': [],
        'metrics' : {
            'topsy:tweets' : 282,
            'topsy:influential_tweets' : 26
        }
    },
    'webpage' : { 
        'aliases': ['url'],
        'biblio': [u'title', "h1"],
        'metrics' : {}
    },
    'wikipedia' : { 
        'aliases': ['doi'],
        'biblio': [],
        'metrics' : {
            'wikipedia:mentions' : 1
        }
    }
}


def request_provider_item(provider, nid, section):
    base_url = 'http://localhost:5001/'
    nid = urlparse.unquote(nid)
    url = base_url + urllib.quote('provider/%s/%s/%s' % (provider, section, nid))
    if options.debug:
        print "\n", url
    req = urllib2.Request(url)
    try:
        response = urllib2.urlopen(req)
        result = json.loads(response.read())
    except urllib2.HTTPError:
        if options.debug:
            print("HTTPError on %s %s %s, perhaps not implemented" % (provider, section, nid))
        result = {}
    if options.debug:
        print result

    return result


def checkItem(provider, id, section, api_response, options):
    if options.debug:
        print "Checking %s result (%s)..." % (provider, id)
    
    # Check aliases are correct
    if section=="aliases":
        aliases = GOLD_RESPONSES[provider]['aliases']
        alias_result = set([namespace for (namespace, nid) in api_response])
        expected_result = set(aliases)
        if (alias_result == expected_result):
            if options.debug:
                print "ALIASES CORRECT! %s" %(alias_result)
        else:
            if options.debug:
                print "ALIASES **NOT** CORRECT, have %s, want %s" %(alias_result, expected_result)
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
            if options.debug:
                print "BIBLIO CORRECT! %s" %(biblio_result)
        else:
            if options.debug:
                print "BIBLIO **NOT** CORRECT, have %s, want %s" %(biblio_result, expected_result)
            return False

    # Check we've got some metric values
    elif section=="metrics":
        metrics = GOLD_RESPONSES[provider]['metrics']
        for metric in metrics.keys():
            try:
                metric_data = api_response[metric]
            except KeyError:
                # didn't return anything.  problem!
                print "METRICS **NOT** CORRECT for %s: metric missing" % (metric)
                pprint(api_response)
                return False

            # expect the returned value to be equal or larger than reference
            if metric_data >= metrics[metric]:
                if options.debug:
                    print "METRICS CORRECT! %s" %(metric_data)
            else:
                if options.debug:
                    print "METRICS **NOT** CORRECT for %s - %s, expected at least %s" % (metric, metric_data, metrics[metric])
                pprint(api_response)
                return False


    return True


def make_call(nid, provider, options):
    all_successful = True
    for section in ["biblio", "aliases", "metrics"]:
        api_response = request_provider_item(provider, nid, section)
        is_response_correct = checkItem(provider,
            nid, 
            section,
            api_response,
            options
        )
        if is_response_correct:
            if not options.quiet:            
                print "happy %s" % section
        else:
            if not options.quiet:            
                print "INCORRECT %s" % section
            all_successful = False
        if options.printdata:
            pprint(api_response)
            print("\n")  
    return(all_successful)


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-s", "--simultaneous", dest="simultaneous", default=1,
                      help="Number of simultaneous requests to make")
    parser.add_option("-q", "--quiet", dest="quiet", default=False, action="store_true", help="Print less output")
    parser.add_option("-v", "--debug", dest="debug", default=False, action="store_true", help="Print debug output")
    parser.add_option("-p", "--printdata", dest="printdata", default=False, 
        action="store_true", help="Display item data")
    (options, args) = parser.parse_args()

    all_successful = True
    for (provider, alias) in REQUEST_IDS:
        print "\n**** %s *****" %(provider.upper())

        (namespace, nid) = alias
        print "\nCANNED DATA"
        canned_success = make_call("example", provider, options)

        print "\nLIVE DATA with item (%s, %s)" %(namespace, nid)
        live_success = make_call(nid, provider, options)
 
        all_successful = all_successful and canned_success and live_success

        time.sleep(0.5)
    if all_successful:
        print "\nAll provider responses were HAPPY."
    else:
        print "\nSome provider responses had errors"

