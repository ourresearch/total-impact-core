# creates all sqlalchemy tables
# will create tables that don't exist yet and leave untouched those already there
# heroku run python extras/db_housekeeping/create_sqlalchemy_tables.py --app total-impact-core-staging

# need to start with the import because that also imports the sqlalchemy class definitions

import argparse
from totalimpact import db

def main(drop = False):
	if drop:
		print "dropping all sqlalchemy tables"
		db.drop_all()
	print "creating all sqlalchemy tables"
	db.create_all()

if __name__ == "__main__":
    # get args from the command line:
    parser = argparse.ArgumentParser(description="create all sql tables")
    parser.add_argument('--drop', 
    	default=False,
    	action='store_true', 
    	help="drop tables before creating them")
    args = vars(parser.parse_args())
    print args
    print "create_sqlalchemy_tables.py starting."
    main(args["drop"])


