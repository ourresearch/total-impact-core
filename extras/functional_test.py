#!/usr/bin/env python
#
# A basic functional test of the total impact API
#

import mechanize
import urllib2
import urllib
import json
import time

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
        item_id = response.read()
        print item_id


ti = TotalImpactAPI()

dryad_item = ti.request_item('doi','10.1186/1745-6215-11-32')
wikipedia_item = ti.request_item('doi', '10.1371/journal.pcbi.1000361')
##wikipedia_item = ti.request_item("url", "http://cottagelabs.com")

github_item = ti.request_item('github', 'egonw/gtd')

time.sleep(10)

print "== Dryad Item =========================================="
print ti.request_item_result(dryad_item)
print "== Wikipedia Item ======================================"
print ti.request_item_result(wikipedia_item)
print "== Github Item ========================================="
print ti.request_item_result(github_item)



