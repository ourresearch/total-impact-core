import couchdb, os, logging, sys

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='%(levelname)8s %(name)s - %(message)s'
)

logger = logging.getLogger("couch_purge")

couch = couchdb.Server(url=os.getenv("CLOUDANT_URL"))
db = couch[os.getenv("CLOUDANT_DB")]
logger.info("connected to couch/ti")

view_name = "admin/bad_dois"

for row in db.view(view_name, include_docs=True):

    doc = row.doc
    logger.info("got doc '{id}' back from {view_name}".format(
        id=row.id,
        view_name=view_name
    ))

    logger.info("doc '{id}' has these doi aliases: {aliases}".format(
        id=row.id,
        aliases=doc["aliases"]["doi"]
    ))

    good_dois = [x for x in doc["aliases"]["doi"] if " []" not in x]
    doc["aliases"]["doi"] = good_dois

    logger.info("saving doc '{id}', which now has these aliases: '{aliases}'".format(
        id=row.id,
        aliases=doc["aliases"]
    ))
    db.save(doc)

logger.info("finished the update.")




