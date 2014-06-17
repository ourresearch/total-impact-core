from totalimpact import default_settings
import os, logging, sys
import analytics
from sqlalchemy import exc
from sqlalchemy import event
from sqlalchemy.pool import Pool
from flask import Flask
from flask.ext.compress import Compress
from flask_sqlalchemy import SQLAlchemy
from flask_debugtoolbar import DebugToolbarExtension
from multiprocessing.util import register_after_fork

# set up logging
# see http://wiki.pylonshq.com/display/pylonscookbook/Alternative+logging+configuration
logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='[%(process)d] %(levelname)8s %(threadName)30s %(name)s - %(message)s'
)

logger = logging.getLogger("ti")



# set up application
app = Flask(__name__)
app.config.from_object(default_settings)
# gzip responses and make it similar on staging and production
Compress(app)
app.config["COMPRESS_DEBUG"] = os.getenv("COMPRESS_DEBUG", "False")=="True"


# database stuff
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_POOL_SIZE"] = 20

db = SQLAlchemy(app)

# see https://github.com/celery/celery/issues/1564
register_after_fork(db.engine, db.engine.dispose)


REDIS_MAIN_DATABASE_NUMBER = 0
REDIS_CELERY_TASKS_DATABASE_NUMBER = 1
REDIS_CELERY_RESULTS_DATABASE_NUMBER = 2
REDIS_CACHE_DATABASE_NUMBER = 7
REDIS_UNITTEST_DATABASE_NUMBER = 8



# from http://docs.sqlalchemy.org/en/latest/core/pooling.html
# This recipe will ensure that a new Connection will succeed even if connections in the pool 
# have gone stale, provided that the database server is actually running. 
# The expense is that of an additional execution performed per checkout
@event.listens_for(Pool, "checkout")
def ping_connection(dbapi_connection, connection_record, connection_proxy):
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("SELECT 1")
    except:
        # optional - dispose the whole pool
        # instead of invalidating one at a time
        # connection_proxy._pool.dispose()

        # raise DisconnectionError - pool will try
        # connecting again up to three times before raising.
        raise exc.DisconnectionError()
    cursor.close()


# config and debugging stuff

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



# set up views and database, if necessary
try:
    from totalimpact import views
except exc.ProgrammingError:
    logger.info("SQLAlchemy database tables not found, so creating them")
    db.session.rollback()
    db.create_all()
    from totalimpact import views

try:
    from totalimpact import extra_schema 
except exc.ProgrammingError:
    logger.info("SQLAlchemy database tables not found, so creating them")
    db.session.rollback()
    db.create_all()
    from totalimpact import extra_schema 



