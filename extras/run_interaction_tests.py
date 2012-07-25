import argparse, redis, os
from totalimpact import fakes

""" Runs interaction tests; takes type of interaction from the argument it's called with."""

# get args from the command line:
parser = argparse.ArgumentParser(description="Run interaction tests from the command line")
parser.add_argument("action_type", type=str, help="The action to test; available actions listed in fakes.py")
args = vars(parser.parse_args())
print args
print "run_interaction_tests.py starting."

person = fakes.Person()
report = person.do(args["action_type"])

redis = redis.from_url(os.getenv("REDISTOGO_URL"))
report_key = args["action_type"] + "_report"
print "saving report in redis with key " + report_key
redis.hmset(report_key, report)





