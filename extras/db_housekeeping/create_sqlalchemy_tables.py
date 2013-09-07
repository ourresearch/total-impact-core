# creates all sqlalchemy tables
# will create tables that don't exist yet and leave untouched those already there
# heroku run python extras/db_housekeeping/create_sqlalchemy_tables.py --app total-impact-core-staging

# need to start with the import because that also imports the sqlalchemy class definitions

from totalimpact import db
db.create_all()



