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
        item_id = json.loads(urllib.unquote(response.read()))
        return item_id

    def request_item_result(self, item_id):
        url = self.base_url + urllib.quote('item/%s' % (item_id))
        req = urllib2.Request(url)
        response = urllib2.urlopen(req)
        return json.loads(response.read())
        

from optparse import OptionParser


def checkItem(item, data, item_type, debug=False):
    checks = {
        'wikipedia' : { 
            'aliases': ['doi'],
            'metrics' : {
                'wikipedia:mentions' : 1
            }
        },
        'github' : { 
            'aliases': ['github'],
            'metrics' : {
                'github:forks' : 0,
                'github:watchers' : 7
            }
        },
        'dryad' : { 
            'aliases': ['doi', 'url', 'title'],
            'metrics' : {
                'dryad:most_downloaded_file' : 63,
                'dryad:package_views' : 149,
                'dryad:total_downloads' : 169
            }
        }
    }

    aliases = checks[item_type]['aliases']
    metrics = checks[item_type]['metrics']

    if debug: print "Checking %s result (%s)..." % (item_type, item)
    
    # Check aliases are correct
    alias_result = set(data['aliases'].keys())
    expected_result = set(aliases + 
        ['created','last_modified','last_completed'])
    if alias_result != expected_result:
        if debug: print "Aliases is not correct, have %s, want %s" %(alias_result, expected_result)
        return False

    # Check we've got some metric values
    for metric in metrics.keys():
        metric_data = data['metrics'][metric]['values']
        if len(metric_data) != 1:
            if debug: print "Incorrect number of metric results for %s - %i" % (metric, len(metric_data))
            return False
        else:
            # expect the returned value to be equal or larger than reference
            if metric_data.values()[0] < metrics[metric]:
                if debug: print "Incorrect metric result for %s - %s, expected at least %s" % (metric, metric_data.values()[0], metrics[metric])
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
    itemid = {}
    for item_type in ['dryad','wikipedia','github']:
        complete[item_type] = {}
        itemid[item_type] = {}

    for idx in range(item_count):
        # Request the items to be generated
        itemid['dryad'][idx] = ti.request_item('doi','10.5061/dryad.7898')
        itemid['wikipedia'][idx] = ti.request_item('doi', '10.1371/journal.pcbi.1000361')
        itemid['github'][idx] = ti.request_item('github', 'egonw/gtd')

    for idx in range(item_count):
        complete['dryad'][idx] = False
        complete['wikipedia'][idx] = False
        complete['github'][idx] = False

    while True:

        for idx in range(item_count):
            for item_type in ['dryad','wikipedia','github']:
                if not complete[item_type][idx]:
                    if options.missing:
                        print item_type, idx, itemid[item_type][idx]
                    
                    itemdata = ti.request_item_result(itemid[item_type][idx])
                    complete[item_type][idx] = checkItem(
                        itemid[item_type][idx], itemdata,
                        item_type, debug=options.missing
                    )
                    if complete[item_type][idx] and options.printdata:
                        pprint(itemdata)

        total = sum([sum(complete[item_type].values()) for item_type in ['dryad','wikipedia','github']])
        print [(item_type, sum(complete[item_type].values())) for item_type in ['dryad','wikipedia','github']], total
        if total == item_count * 3:
            sys.exit(0)    

        time.sleep(0.5)

