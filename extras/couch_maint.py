import couchdb, os, logging, sys

# run in heroku with:
# heroku run python extras/couch_maint.py

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='%(levelname)8s %(name)s - %(message)s'
)

logger = logging.getLogger("couch_maint")

### CAREFUL!  

production = False

if (production):
    print "USING PRODUCTION DB!!!! STOP NOW IF THIS ISNT WHAT YOU WANT!!!!"
    ### THIS IS THE PRODUCTION DB!
    # comment out when false for extra protection!!!!
    #cloudant_db = "ti"
    #cloudant_url = "https://app5109761.heroku:TuLL8oXFh4k0iAcAPnDMlSjC@app5109761.heroku.cloudant.com"
    pass    
else:    
    cloudant_db = os.getenv("CLOUDANT_DB")
    cloudant_url = os.getenv("CLOUDANT_URL")

couch = couchdb.Server(url=cloudant_url)
db = couch[cloudant_db]
logger.info("connected to couch at " + cloudant_url + " / " + cloudant_db)

"""
admin/bad_pmid

function(doc) {
  if (doc.type == "item") {
    if (typeof doc.aliases.pmid != "undefined") {
      if (doc.aliases.pmid[0] == "22771269") {
     emit(doc._id, 1);
      }
    }
  }
}"""
def del_bad_pmids():
    view_name = "admin/bad_pmid"
    tiids = []
    for row in db.view(view_name, include_docs=True):
        tiid = row.id
        tiids += [tiid]
        logger.info("got tiid {tiid}".format(
            tiid=tiid))

        del(row.doc["aliases"]["pmid"])

        logger.info("saving doc '{id}', which now has these aliases: '{aliases}'".format(
            id=row.id,
            aliases=row.doc["aliases"]
        ))
        db.save(row.doc)

    logger.info("finished looking, found {num_tiids} tiids with pmids".format(
        num_tiids=len(tiids)))


def find_all_pmccitation_snaps():
    view_name = "admin/snaps_by_metric_name"
    snap_ids = []
    for row in db.view(view_name, include_docs=True, key="pubmed:pmc_citations"):
        snap_id = row.value
        snap_ids += [snap_id]
        #logger.info("pmc snap id {snap_id}".format(snap_id=snap_id))
        #db.delete(row.doc)
    logger.info("finished looking, found {num} tiids".format(num=len(snap_ids)))


def find_all_tiids_w_pmccitation_snaps():
    view_name = "admin/tiids_w_pmc_snaps"
    tiids = []
    for row in db.view(view_name, group=True, include_docs=False):
        tiid = row.key
        tiids += [tiid]
        number_snaps = row.value
        logger.info("tiid {tiid} had {number_snaps} pmc snaps".format(
            tiid=tiid, 
            number_snaps=number_snaps
        ))
    logger.info("finished looking, found {num_tiids} tiids".format(num_tiids=len(tiids)))


def wikipedia_snap_cleanup():
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

"""
admin/multiple_dois

function(doc) {
    // lists tiids by individual alias namespaces and ids
    if (doc.type == "item") {
        // expecting every alias object has a tiid
        tiid = doc["_id"];
    if (typeof doc.aliases.doi != "undefined") {
       if (doc.aliases.doi.length > 1) {
           emit(doc.aliases.doi.length, doc)
       }
    }
    }
}
"""
def bad_doi_cleanup():
    view_name = "admin/multiple_dois"
    bad_doi = '10.1016/j.eururo.2012.06.052'
    bad_title = "Reply from Authors re: Ricarda M. Bauer. Female Slings: Where Do We Stand? Eur Urol. In press. http://dx.doi.org/10.1016/ j.eururo.2012.05.036"
    bad_url = "http://linkinghub.elsevier.com/retrieve/pii/S030228381200766X"

    changed_rows = 0
    for row in db.view(view_name, include_docs=True):

        doc = row.doc
        logger.info("got doc '{id}' back from {view_name}".format(
            id=row.id,
            view_name=view_name
        ))

        if (bad_doi in doc["aliases"]["doi"]):
            print "\ngot a bad one!"

            logger.info("doc '{id}' has these doi aliases: {aliases}".format(
                id=row.id,
                aliases=doc["aliases"]
            ))

            good_dois = [x for x in doc["aliases"]["doi"] if bad_doi not in x]
            doc["aliases"]["doi"] = good_dois

            good_titles = [x for x in doc["aliases"]["title"] if bad_title not in x]
            doc["aliases"]["title"] = good_titles

            good_urls = [x for x in doc["aliases"]["url"] if bad_url not in x]
            doc["aliases"]["url"] = good_urls

            logger.info("saving doc '{id}', which now has these aliases: '{aliases}'".format(
                id=row.id,
                aliases=doc["aliases"]
            ))
            db.save(doc)
            changed_rows += 1

    logger.info("finished the update.")
    logger.info("changed %i rows" %changed_rows)


bad_doi_cleanup()

# remove all pmids
# remove all doi '10.1016/j.eururo.2012.06.052'
# remove all pmc snaps of the three datatypes

# remove all \b
