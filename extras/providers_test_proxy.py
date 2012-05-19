#!/usr/bin/env python
#
# Providers Test Proxy
#
# This is a very basic webserver which can be used to simluate commuicating
# providers. It performs basic response replay for known data items. Response
# data is stored in test/data/<provider>
#

from SimpleHTTPServer import SimpleHTTPRequestHandler
from BaseHTTPServer import BaseHTTPRequestHandler
import SocketServer
from optparse import OptionParser
import logging
import os

import daemon
import lockfile
from totalimpact.pidsupport import PidFile

responses = {'dryad':{},'wikipedia':{},'github':{}}

def load_test_data(provider, filename):
    datadir = os.path.join(os.path.split(__file__)[0], "../test/data/", provider)
    return open(os.path.join(datadir, filename)).read()

responses['dryad']['aliases'] = load_test_data('dryad', 'sample_extract_aliases_page.xml')
responses['dryad']['metrics'] = load_test_data('dryad', 'sample_extract_metrics_page.html')
responses['dryad']['10.5061'] = load_test_data('dryad', 'dryad_info_10.5061.xml')
responses['wikipedia']['metrics'] = load_test_data('wikipedia', 'wikipedia_response.xml')
responses['wikipedia']['10.1186'] = load_test_data('wikipedia', 'wikipedia_10.1186_response.xml')
responses['wikipedia']['10.5061'] = load_test_data('wikipedia', 'wikipedia_10.5061_response.xml')
responses['wikipedia']['cottagelabs'] = load_test_data('wikipedia', 'wikipedia_cottagelabs.xml')
responses['github']['members'] = load_test_data('github', 'egonw_gtd_member_response.json')
responses['github']['metrics'] = load_test_data('github', 'egonw_gtd_metric_response.json')

urlmap = {

    ###################################################################################
    ##
    ## Dryad Provider
    ##  

    "http://datadryad.org/solr/search/select/?q=dc.identifier:10.5061/dryad.7898&fl=dc.identifier.uri,dc.title": responses['dryad']['aliases'],
    "http://datadryad.org/solr/search/select/?q=dc.identifier:10.5061/dryad.7898&fl=dc.date.accessioned.year,dc.identifier.uri,dc.title_ac,dc.contributor.author_ac" : responses['dryad']['10.5061'],
    "http://dx.doi.org/10.5061/dryad.7898": responses['dryad']['metrics'],

    ###################################################################################
    ##
    ## Wikipedia Provider
    ##

    # Metrics information for various test items
    "http://en.wikipedia.org/w/api.php?action=query&list=search&srprop=timestamp&format=xml&srsearch='10.1371/journal.pcbi.1000361'": responses['wikipedia']['metrics'],
    "http://en.wikipedia.org/w/api.php?action=query&list=search&srprop=timestamp&format=xml&srsearch='10.1186/1745-6215-11-32'": responses['wikipedia']['10.1186'],
    "http://en.wikipedia.org/w/api.php?action=query&list=search&srprop=timestamp&format=xml&srsearch='10.5061/dryad.7898'": responses['wikipedia']['10.5061'],
    "http://en.wikipedia.org/w/api.php?action=query&list=search&srprop=timestamp&format=xml&srsearch='http://cottagelabs.com'": responses['wikipedia']['cottagelabs'],

    ###################################################################################
    ##
    ## Github Provider
    ##

    # member_items results for egonw
    "https://api.github.com/users/egonw/repos": responses['github']['members'],
    # metrics results for ('github', 'egonw,gtd')
    "https://github.com/api/v2/json/repos/show/egonw/gtd": responses['github']['metrics'],

    ###################################################################################
    ##
    ## Test Item
    ##
    ## This is just so you can check http://proxy:port/test to see if this is running ok
    ##

    "/test": responses['github']['members'],
}

class ProvidersTestProxy(BaseHTTPRequestHandler):

    def do_GET(self):
        if urlmap.has_key(self.path):
            print "Found:", self.path
            self.send_response(200)
            self.end_headers()
            self.wfile.write(urlmap[self.path])
        else: 
            print "Not Found:", self.path
            self.send_response(500, "Test Proxy: Unknown URL")

if __name__ == '__main__':

    parser = OptionParser()
    parser.add_option("-p", "--port",
                      action="store", dest="port", default=8081,
                      help="Port to run the server on (default 8081)")
    parser.add_option("-i", "--pid",
                      action="store", dest="pid", default=None,
                      help="pid file")
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose", default=False,
                      help="print debugging output")
    parser.add_option("-d", "--daemon",
                      action="store_true", dest="daemon", default=False,
                      help="run as a daemon")
    parser.add_option("-l", "--log",
                      action="store", dest="log", default=None,
                      help="runtime log")
    parser.add_option("-q", "--quiet",
                      action="store_true", dest="quiet", default=False,
                      help="Only print errors on failures")

    (options, args) = parser.parse_args()

    if options.verbose:
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        # Nicer formatting to show different providers
        formatter = logging.Formatter('  %(name)s - %(message)s')
        ch.setFormatter(formatter)
        logger = logging.getLogger('')
        logger.addHandler(ch)
    else:
        logger = logging.getLogger('totalimpact.providers')
        logger.setLevel(logging.WARNING)

    class ReuseServer(SocketServer.TCPServer):
        allow_reuse_address = True

    if not options.daemon:
        handler = ProvidersTestProxy
        httpd = ReuseServer(("", int(options.port)), handler)
        print "listening on port", options.port
        httpd.serve_forever()
    else:
        rootdir = os.path.dirname(os.path.dirname(__file__))
        context = daemon.DaemonContext()
        if options.log:
            logfile = options.log
        else:
            logfile = os.path.join(rootdir, 'logs', 'proxy.log')
        output = open(logfile,'w+')
        context.stderr = output
        context.stdout = output
        if options.pid:
            context.pidfile = PidFile(options.pid)
        else: 
            context.pidfile = PidFile(os.path.join(rootdir, 'run', 'proxy.pid'))
        context.working_directory = rootdir
        with context:
            handler = ProvidersTestProxy
            httpd = ReuseServer(("", int(options.port)), handler)
            print "listening on port", options.port
            httpd.serve_forever()

    

