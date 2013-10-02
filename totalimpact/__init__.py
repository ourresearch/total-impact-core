from totalimpact import default_settings
import os, logging, sys
import analytics
import sqlalchemy.exc
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_debugtoolbar import DebugToolbarExtension

# see http://wiki.pylonshq.com/display/pylonscookbook/Alternative+logging+configuration
logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='[%(process)d] %(levelname)8s %(threadName)30s %(name)s - %(message)s'
)

logger = logging.getLogger("ti")


app = Flask(__name__)
app.config.from_object(default_settings)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("POSTGRESQL_URL")
app.config["SQLALCHEMY_POOL_SIZE"] = 50
# app.config["SQLALCHEMY_ECHO"] = True
# app.config["SQLALCHEMY_RECORD_QUERIES"] = True

db = SQLAlchemy(app)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
# set up Flask-DebugToolbar
if (os.getenv("FLASK_DEBUG", False) == "True"):
    logger.info("Setting app.debug=True; Flask-DebugToolbar will display")
    app.debug = True
    app.config["DEBUG_TB_INTERCEPT_REDIRECTS"] = False
toolbar = DebugToolbarExtension(app)


# segment.io logging
analytics.init(os.getenv("SEGMENTIO_PYTHON_KEY"))
analytics.identify("CORE", {
				       'internal': True,
				       'name': 'IMPACTSTORY CORE'})

try:
	from totalimpact import views
except sqlalchemy.exc.ProgrammingError:
	logger.info("SQLAlchemy database tables not found, so creating them")
	db.session.rollback()
	db.create_all()
	from totalimpact import views

try:
	from totalimpact import extra_schema 
except sqlalchemy.exc.ProgrammingError:
	logger.info("SQLAlchemy database tables not found, so creating them")
	db.session.rollback()
	db.create_all()
	from totalimpact import extra_schema 

