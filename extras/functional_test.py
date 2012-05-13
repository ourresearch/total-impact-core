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

request_ids = {"dryad": ('doi','10.5061/dryad.7898')} 
#                "wikipedia": ('doi', '10.1371/journal.pcbi.1000361'), 
#                "github": ('github', 'egonw/gtd')}

PORT = 5001

class TotalImpactAPI:
    base_url = 'http://localhost:' + str(PORT) + '/'
    ###base_url = '/'

    def request_item(self, namespace, nid):
        """ Attempt to obtain an item from the server using the given
            namespace and namespace id. For example, 
              namespace = 'pubmed', nid = '234234232'
            Will request the item related to pubmed item 234234232
        """

        url = self.base_url + urllib.quote('item/%s/%s' % (namespace, nid))
        req = urllib2.Request(url)
        data = {} # fake a POST

        response = urllib2.urlopen(req, data)
        tiid = json.loads(urllib.unquote(response.read()))
        ###response = client.post(url)
        ###tiid = json.loads(response.data)

        return tiid

    def request_item_result(self, tiid):
        url = self.base_url + urllib.quote('item/%s' % (tiid))
        req = urllib2.Request(url)
        response = urllib2.urlopen(req)
        result = json.loads(response.read())

        ###response = client.get(url)
        ###result = json.loads(response.data)

        return result
        

    def request_provider_item(self, provider, section, nid):
        url = self.base_url + urllib.quote('provider/%s/%s/%s' % (provider, section, nid))
        print url
        req = urllib2.Request(url)
        response = urllib2.urlopen(req)
        result = json.loads(response.read())

        ###response = client.get(url)
        ###result = json.loads(response.data)

        return result

from optparse import OptionParser


def checkItem(section, id, api_response, provider, debug=False):
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


    if debug: 
        print "Checking %s result (%s)..." % (provider, id)
    
    # Check aliases are correct
    if section=="aliases":
        aliases = checks[provider]['aliases']
        alias_result = set([namespace for (namespace, nid) in api_response])
        expected_result = set(aliases + 
            ['created','last_modified','last_completed'])
        if alias_result != expected_result:
            if debug: 
                print "Aliases is not correct, have %s, want %s" %(alias_result, expected_result)
            return False

    # Check biblio are correct
    if section=="biblio":
        biblio = checks[provider]['biblio']    
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
    if section=="metrics":
        metrics = checks[provider]['metrics']
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

    parser = OptionParser()
    parser.add_option("-s", "--simultaneous", dest="simultaneous", default=1,
                      help="Number of simultaneous requests to make")
    parser.add_option("-m", "--missing", dest="missing", default=False, action="store_true",
                      help="Display any outstanding items")
    parser.add_option("-p", "--printdata", dest="printdata", default=False, action="store_true",
                      help="Display item data")
    (options, args) = parser.parse_args()


    ti = TotalImpactAPI()
    complete = {}
    final_responses = {}
    providers = request_ids.keys()

    ###from totalimpact import api
    ###app = api.app
    ###app.testing = True
    ###client = app.test_client()
    
    #### setup the database
    ###testing_db_name = "functional_test"
    ###app.config["DB_NAME"] = testing_db_name
    ###for provider in providers:
    ###    for template_type in ["metrics", "members", "aliases", "biblio"]:
    ###        url = "http://localhost:8080/" + provider + "/" + template_type + "?%s"
    ###        app.config["PROVIDERS"][provider][template_type+"_url"] = url

    for provider in providers:
        complete[provider] = {}
        final_responses[provider] = {}
        (namespace, nid) = request_ids[provider]
        complete[provider] = {}
        if options.missing:
            print provider, nid
        for section in ["biblio", "aliases", "metrics"]:
            api_response = ti.request_provider_item(provider, section, nid)
            final_responses[provider][section] = api_response
            complete[provider][section] = checkItem(section,
                nid,
                api_response,
                provider, 
                debug=options.missing
            )
            if complete[provider] and options.printdata:
                pprint(api_response)


        #total = sum([sum(complete[provider].values()) for provider in providers])
        #print [(provider, sum(complete[provider].values())) for provider in providers], total
        #if total == item_count * len(providers):
        #    pprint(final_responses)
        #    sys.exit(0)    

        time.sleep(0.5)

