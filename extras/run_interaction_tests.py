import syslog, sys, argparse

""" This file runs the method accessed from the /tests/interactions endpoint.

It's a hack to get around the fact we use the Flask webserver in local testing;
this webserver can only handle one request at a time. If it's serving the test
request, it can't also server the API requests that the test method makes."""

'''
class StdOut(object):
    """ subclass stdout to send everything to the logger
    """
    def write(self, string):
        syslog.syslog(string)

# syslog will push to local3, which is formatted to push stuff to papertrail
syslog.openlog(facility=syslog.LOG_LOCAL3)

# stdout won't be sent to terminal, but rather to logger.
sys.stdout = StdOut()
'''

# we have to do the import down here, so that totalimpact logging will use our new stdout
from totalimpact import views

# get args from the command line:
parser = argparse.ArgumentParser(description="Run interaction tests from the command line")
parser.add_argument("action_type", type=str, help="The action to test; available actions listed in fakes.py")
args = vars(parser.parse_args())
print "run_interaction_tests.py starting."

report = views.tests_interactions("make_collection", web=False)
print "run_interaction_tests.py finished. Report: " + str(report)