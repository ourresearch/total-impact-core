import couchdb, os, logging, sys

# run in heroku with:
# heroku run python extras/couch_purge.py

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='%(levelname)8s %(name)s - %(message)s'
)

logger = logging.getLogger("couch_purge")

couch = couchdb.Server(url=os.getenv("CLOUDANT_URL"))
db = couch[os.getenv("CLOUDANT_DB")]
logger.info("connected to couch/" + os.getenv("CLOUDANT_DB"))

view_name = "admin/old-wikipedia-snaps"

for row in db.view(view_name, include_docs=True):

    doc = row.doc
    logger.info("got doc '{id}' back from {view_name}, with drilldown_url {url}".format(
        id=row.id,
        view_name=view_name,
        url=doc["drilldown_url"]

    ))
    logger.info("deleting doc '{id}'.".format(
        id=row.id
    ))
    db.delete(doc)

logger.info("finished the update.")




