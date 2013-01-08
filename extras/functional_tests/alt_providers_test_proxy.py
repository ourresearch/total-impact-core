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


class ProvidersTestProxy(BaseHTTPRequestHandler):

    def do_GET(self):
        datadir = os.path.join(os.path.split(__file__)[0], "sample_provider_pages")

        # remove the first character because includes /
        submitted_url = self.path[1:len(self.path)+1]
        # separate everything after & because is id
        try:
            (url_part, arg_part) = submitted_url.split("?")
        except ValueError:
            url_part = submitted_url

        # don't try to serve up the favicon, just exit
        if url_part == "favicon.ico":
            return

        sample_provider_page_path = os.path.join(datadir, url_part)
        print sample_provider_page_path
        try:
            text = open(sample_provider_page_path).read()
            print text
            print "Found:", submitted_url
            self.send_response(200)
            self.end_headers()
            self.wfile.write(text)
        except IOError:
            print "Not Found:", submitted_url
            self.send_response(500, "Test Proxy: Unknown URL")
        print "done with do_GET"



if __name__ == '__main__':

    parser = OptionParser()
    parser.add_option("-p", "--port",
                      action="store", dest="port", default=8080,
                      help="Port to run the server on (default 8080)")
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose", default=False,
                      help="print debugging output")

    (options, args) = parser.parse_args()

    if not options.verbose:
        logger = logging.getLogger('ti.providers')
        logger.setLevel(logging.WARNING)

    class ReuseServer(SocketServer.TCPServer):
        allow_reuse_address = True

    handler = ProvidersTestProxy
    httpd = ReuseServer(("", int(options.port)), handler)
    print "listening on port", options.port
    httpd.serve_forever()


