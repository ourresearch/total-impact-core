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
        print url
        req = urllib2.Request(url)
        data = {} # fake a POST
        response = urllib2.urlopen(req, data)
        item_id = json.loads(urllib.unquote(response.read()))
        return item_id

    def request_item_result(self, item_id):
        url = self.base_url + urllib.quote('item/%s' % (item_id))
        req = urllib2.Request(url)
        response = urllib2.urlopen(req)
        return json.loads(response.read())
        


from optparse import OptionParser

TEST_ITEMS = {
#                ('doi', '10.1371/journal.pcbi.1000361')), 
#                ("delicious", ('url', 'http://total-impact.org/')),
                ('doi','10.5061/dryad.18') : 
                    { 
                        'aliases': ['doi', 'url', 'title'],
                        'biblio': [u'authors', u'year', u'repository', u'title'],
                        'metrics' : {
                            'dryad:most_downloaded_file' : 63,
                            'dryad:package_views' : 149,
                            'dryad:total_downloads' : 169
                        }
                    }
#                ("github", ('github', 'egonw,cdk')),
#                ("mendeley", ('doi', '10.1371/journal.pcbi.1000361')), 
#                ("topsy", ('url', 'http://total-impact.org')),
#                ("webpage", ('url', 'http://nescent.org/')),
#                ("wikipedia", ('doi', '10.1371/journal.pcbi.1000361')) 
}

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
        'aliases': ['doi', "url"],
        'biblio': [],
        'metrics' : {
            'wikipedia:mentions' : 1
        }
    }
}




def checkItem(item, data, alias, options):
    debug = options.debug
    if debug: print "Checking %s result (%s)..." % (alias, item)
    
        # Check aliases are correct
#    for section in ["biblio", "aliases", "metrics"]:
    for section in ["aliases"]:

        result = checkItemSection(alias, item, section, data[section], options)
        if not result:
            return False
    return True

def checkItemSection(alias, id, section, api_response, options):
    if options.debug:
        print "Checking %s result (%s)..." % (alias, id)

    # Check aliases are correct
    if section=="aliases":
        aliases = TEST_ITEMS[alias]['aliases']
        print api_response
        alias_result = set(api_response.keys())
        expected_result = set(aliases + [u'last_modified', u'created'])
        if (alias_result == expected_result):
            if options.debug:
                print "ALIASES CORRECT! %s" %(alias_result)
        else:
            if options.debug:
                print "ALIASES **NOT** CORRECT, have %s, want %s" %(alias_result, expected_result)
            return False

    # Check biblio are correct
    elif section=="biblio":
        biblio = TEST_ITEMS[alias]['biblio']    
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
        metrics = TEST_ITEMS[alias]['metrics']
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


def make_call(nid, alias, options):
    all_successful = True
    for section in ["biblio", "aliases", "metrics"]:
        api_response = request_alias_item(alias, nid, section)

        is_response_correct = checkItem(alias,
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
    parser.add_option("-m", "--missing", dest="missing", default=False, action="store_true",
                      help="Display any outstanding items")
    parser.add_option("-p", "--printdata", dest="printdata", default=False, action="store_true",
                      help="Display item data")
    parser.add_option("-d", "--debug", dest="debug", default=False, action="store_true",
                      help="Display item data")
    (options, args) = parser.parse_args()


    item_count = int(options.simultaneous)
    
    ti = TotalImpactAPI()

    complete = {}
    itemid = {}
    aliases = TEST_ITEMS.keys()

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
                        options
                    )
                    if complete[alias][idx] and options.printdata:
                        pprint(itemdata)

        total = sum([sum(complete[alias].values()) for alias in aliases])
        print [(alias, sum(complete[alias].values())) for alias in aliases], total
        if total == item_count * len(aliases):
            sys.exit(0)    

        time.sleep(0.5)

