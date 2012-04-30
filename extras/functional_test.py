#!/usr/bin/env python
#
# A basic functional test of the total impact API
#

import mechanize
import urllib2
import urllib
import json
import time
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
        print url
        req = urllib2.Request(url)
        response = urllib2.urlopen(req)
        return json.loads(response.read())
        


ti = TotalImpactAPI()

# Request the items to be generated
dryad_item = ti.request_item('doi','10.5061/dryad.7898')
wikipedia_item = ti.request_item('doi', '10.1371/journal.pcbi.1000361')
github_item = ti.request_item('github', 'egonw/gtd')

time.sleep(10)

# Try and get the result
dryad_data = ti.request_item_result(dryad_item)
wikipedia_data = ti.request_item_result(wikipedia_item)
github_data = ti.request_item_result(github_item)

checks = {
    'wikipedia' : { 
        'item': wikipedia_item,
        'data': wikipedia_data,
        'aliases': ['doi'],
        'metrics' : {
            'wikipedia:mentions' : 1
        }
    },
    'github' : { 
        'item': github_item,
        'data': github_data,
        'aliases': ['github'],
        'metrics' : {
            'github:forks' : 0,
            'github:watchers' : 7
        }
    },
    'dryad' : { 
        'item': dryad_item,
        'data': dryad_data,
        'aliases': ['doi'],
        'metrics' : {
            'dryad:most_downloaded_file' : 63,
            'dryad:package_views' : 149,
            'dryad:total_downloads' : 169
        }
    }
}


for provider in checks.keys():
    item = checks[provider]['item']
    data = checks[provider]['data']
    aliases = checks[provider]['aliases']
    metrics = checks[provider]['metrics']

    print "Checking %s result (%s)..." % (provider, item)
    
    # Check aliases are correct
    alias_result = set(data['aliases'].keys())
    if alias_result != set(['created','last_modified','last_completed'] + aliases):
        print "Aliases is not correct, have %s" % alias_result

    # Check we've got some metric values
    for metric in metrics.keys():
        metric_data = data['metrics'][metric]['values']
        if len(metric_data) != 1:
            print "Incorrect number of metric results for %s - %i" % (metric, len(metric_data))
        else:
            if metric_data.values()[0] != metrics[metric]:
                print "Incorrect metric result for %s - %s" % (metric, metric_data.values()[0])


