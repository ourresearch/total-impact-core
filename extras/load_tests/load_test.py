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
            'aliases': ['github', 'url', 'title'],
            'metrics' : {
                'github:forks' : 0,
                'github:watchers' : 7
            }
        },
        'dryad' : { 
            'aliases': ['doi','url','title'],
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
    if alias_result != set(['created','last_modified','last_completed'] + aliases):
        if debug: print "Aliases is not correct, have %s" % alias_result
        return False

    # Check we've got some metric values
    for metric in metrics.keys():
        metric_data = data['metrics'][metric]['values']
        if len(metric_data) != 1:
            if debug: print "Incorrect number of metric results for %s - %i" % (metric, len(metric_data))
            return False
        else:
            if metric_data.values()[0] < metrics[metric]:
                if debug: print "Incorrect metric result for %s - %s" % (metric, metric_data.values()[0])
                return False

    return True





from twisted.internet import reactor
from twisted.web.client import getPage 

total_responses = 0

REQUEST_DETAILS_RETRY_DELAY=5

class TotalImpactAPIAsync:
    base_url = 'http://localhost:5001/'
    debug = False
    
    def __init__(self):
        self.item_ids = {}
        self.item_details = {}
        self.total_responses = 0
        self.details_responses = 0
        self.item_idx = 0
    
    def handleRequestItemResponse(self, response, idx):
        if self.debug: print 'Response received for %i' % idx
        self.item_ids[idx] = json.loads(urllib.unquote(response))
        self.total_responses += 1

    def handleRequestItemFailure(self, failure, idx):
        print 'Failure received for %i' % idx, failure
        self.total_responses += 1
        reactor.stop()

    def handleItemDetailsResponse(self, response, idx, item_type, count):
        if self.debug: print 'Details received for %i' % idx
        self.item_details[idx] = json.loads(urllib.unquote(response))
        if not checkItem(self.item_ids[idx], self.item_details[idx], item_type):
            # This item isn't read yet, lets keep re-requesting
            if self.debug: print "not ready yet, calling later"
            reactor.callLater(REQUEST_DETAILS_RETRY_DELAY, self._request_details, idx, item_type, count+1)
        else:
            self.details_responses += 1

    def handleItemDetailsFailure(self, failure, idx):
        print 'Item details failed for %i' % idx, failure
        self.details_responses += 1
        reactor.stop()

    def request_item(self, namespace, nid):
        """ Attempt to obtain an item from the server using the given
            namespace and namespace id. For example, 
              namespace = 'pubmed', nid = '234234232'
            Will request the item related to pubmed item 234234232
        """
        url = self.base_url + urllib.quote('item/%s/%s' % (namespace, nid))
        d = getPage(url, method='POST')
        idx = self.item_idx
        self.item_idx += 1
        d.addCallback(self.handleRequestItemResponse, idx)
        d.addErrback(self.handleRequestItemFailure, idx)
        return idx

    def request_details(self, idx, item_type):
        """ Get an item's details. Keep retrying until results 
            are obtained and valid """
        return self._request_details(idx, item_type, count=1)
   
    def _request_details(self, idx, item_type, count=1):
        item_id = self.item_ids[idx]
        url = self.base_url + urllib.quote('item/%s' % (item_id))
        if self.debug: print "Getting %i / %s" % (idx, url)
        d = getPage(url, method='GET')
        d.addCallback(self.handleItemDetailsResponse, idx, item_type, count)
        d.addErrback(self.handleItemDetailsFailure, idx)


class TotalImpactTest:
    """ Controller for handling the sequence of operations
        asynchronously.
    """

    def __init__(self, item_count):
        self.ti = TotalImpactAPIAsync()
        self.item_count = item_count
        self.itemid = {}
        for item_type in ['dryad','wikipedia','github']:
            self.itemid[item_type] = {}

    # Flow Methods ##############################################

    def runTests(self):
        self.requestItems()
        reactor.callLater(1, self.waitForRequestsToComplete)

    def waitForRequestsToComplete(self):
        if self.ti.total_responses != self.item_count * 3:
            print "Requesting items (%i/%i)" % (self.ti.total_responses, self.item_count * 3)
            reactor.callLater(1, self.waitForRequestsToComplete)
        else:
            print "All items requested, now waiting for results"
            self.getItemResults()
            reactor.callLater(1, self.waitForDetailsToComplete)
    
    def waitForDetailsToComplete(self):
        if self.ti.details_responses != self.item_count * 3:
            print "Results received (%i/%i)" % (self.ti.details_responses, self.item_count * 3)
            reactor.callLater(1, self.waitForDetailsToComplete)
        else:
            print "All details complete"
            reactor.stop()

    #############################################################

    def getItemResults(self):
        for idx in range(self.item_count):
            for item_type in ['dryad','wikipedia','github']:
                self.ti.request_details(self.itemid[item_type][idx], item_type)

    def requestItems(self):
        for idx in range(self.item_count):
            # Request the items to be generated
            self.itemid['dryad'][idx] = self.ti.request_item('doi','10.5061/dryad.7898')
            self.itemid['wikipedia'][idx] = self.ti.request_item('doi', '10.1371/journal.pcbi.1000361')
            self.itemid['github'][idx] = self.ti.request_item('github', 'egonw,cdk')



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
    
    tester = TotalImpactTest(item_count)
    tester.runTests()
    reactor.run()

    print "The following are not yet complete..."

    # Print anything outstanding
    for item_type in ['dryad','wikipedia','github']:
        for idx in tester.itemid[item_type].values():
            if not checkItem(tester.ti.item_ids[idx], tester.ti.item_details[idx], item_type):
                print item_type, tester.ti.item_ids[idx]

