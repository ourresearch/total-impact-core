import argparse, redis, os
from totalimpact import testers

""" Runs interaction tests; takes type of interaction from the argument it's called with."""

# get args from the command line:
parser = argparse.ArgumentParser(description="Run interaction tests from the command line")
parser.add_argument("action_type", type=str, help="The action to test; available actions listed in fakes.py")
args = vars(parser.parse_args())
print args
print "run_collection_test.py starting."

# this assumes you're testing collections; must be adapted when we add provider tests...
collection_tester = testers.CollectionTester()
report = collection_tester.test(args["action_type"])

# storing them in redis so we can look at them in the /test/collection/<create|read> report
redis = redis.from_url(os.getenv("REDISTOGO_URL"))
report_key = "test.collection." + args["action_type"]
print "saving report in redis with key " + report_key
redis.hmset(report_key, report)





