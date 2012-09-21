import couchdb, os, logging, sys
from pprint import pprint
import time

# run in heroku by a) commiting, b) pushing to heroku, and c) running
# heroku run python extras/couch_maint.py

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='%(levelname)8s %(name)s - %(message)s'
)

logger = logging.getLogger("couch_maint")
  
cloudant_db = os.getenv("CLOUDANT_DB")
cloudant_url = os.getenv("CLOUDANT_URL")

couch = couchdb.Server(url=cloudant_url)
db = couch[cloudant_db]
logger.info("connected to couch at " + cloudant_url + " / " + cloudant_db)

"""
admin/items_with_pmids

function(doc) {
  if (doc.type == "item") {
    if (typeof doc.aliases.pmid != "undefined") {
     emit(doc._id, 1);
    }
  }
}"""
def del_pmids():
    view_name = "admin/items_with_pmids"
    tiids = []
    for row in db.view(view_name, include_docs=True):
        tiid = row.id
        tiids += [tiid]
        del(row.doc["aliases"]["pmid"])
        logger.info("saving doc '{id}'".format(id=row.id))
        db.save(row.doc)

    logger.info("finished looking, found {num_tiids} tiids with pmids".format(
        num_tiids=len(tiids)))



"""
admin/multiple_dois

function(doc) {
    // lists tiids by individual alias namespaces and ids
    if (doc.type == "item") {
        // expecting every alias object has a tiid
        tiid = doc["_id"];
    if (typeof doc.aliases.doi != "undefined") {
       if (doc.aliases.doi.length > 1) {
           emit(doc._id, 1)
       }
    }
    }
}

admin/collections_by_tiid
function(doc) {
    // lists tiids by individual alias namespaces and ids
    if (doc.type == "collection") {
    doc.item_tiids.forEach(function(tiid) {
           emit(tiid, doc._id)
        })
   }
}

admin/snaps_by_tiid
function(doc) {
    // lists tiids by individual alias namespaces and ids
    if (doc.type == "metric_snap") {
       emit(doc.tiid, doc._id)
   }
}
"""
def bad_doi_cleanup():
    view_name = "admin/multiple_dois"

    changed_rows = 0
    for row in db.view(view_name, include_docs=True):

        logger.info("got doc '{id}' back from {view_name}".format(
            id=row.id,
            view_name=view_name
        ))

        doc = row.doc
        tiid = row.id

        logger.info("\n\nPROCESSING ITEM {id}".format(id=tiid))            
        pprint(doc["aliases"])

        # delete tiid from collections
        collections_with_tiid = db.view("admin/collections_by_tiid", include_docs=True, key=tiid)
        for collection_row in collections_with_tiid:
            collection = collection_row.doc
            logger.info("deleting from collection {id}".format(id=collection_row.id))
            #pprint(collection)            
            good_tiids = [x for x in collection["item_tiids"] if tiid not in x]
            collection["item_tiids"] = good_tiids
            db.save(collection)

        # delete snaps
        snaps_with_tiid = db.view("admin/snaps_by_tiid", include_docs=True, key=tiid)
        for snap_row in snaps_with_tiid:
            snap = snap_row.doc
            pprint(snap)            
            logger.info("deleting SNAP {id}".format(id=snap_row.id))            
            db.delete(snap)

        # delete the item
        logger.info("deleting item {id}".format(id=tiid))            
        db.delete(doc)

        changed_rows += 1

    logger.info("finished the update.")
    logger.info("changed %i rows" %changed_rows)


"""
function(doc) {
    emit([doc.type, doc._id], doc);
}
"""
def build_alias_items_in_collections():
    view_name = "queues/by_type_and_id"
    view_rows = db.view(view_name, 
            include_docs=True, 
            start_key=["collection", "0000000000"], 
            endkey=["collection", "zzzzzzzzzz"])
    total_rows = len(view_rows)
    logger.info("total rows = %i" % total_rows)
    row_count = 0

    for row in view_rows:
        row_count += 1
        logger.info("now on rows = %i of %i, id %s" % (row_count, total_rows, row.id))
        collection = row.doc
        #pprint(collection)
        if collection.has_key("alias_tiids"):
            logger.info("skipping")
        else:
            item_tiids = collection["item_tiids"]
            alias_tiids = dict(zip(["unknown-"+tiid for tiid in item_tiids], item_tiids))
            collection["alias_tiids"] = alias_tiids
            db.save(collection)
            logger.info("saving")



"""
function(doc) {
    emit([doc.type, doc._id], doc);
}
"""
def delete_item_tiids_from_collection():
    view_name = "queues/by_type_and_id"
    view_rows = db.view(view_name, 
            include_docs=True, 
            start_key=["collection", "0000000000"], 
            endkey=["collection", "zzzzzzzzzz"])
    total_rows = len(view_rows)
    logger.info("total rows = %i" % total_rows)
    row_count = 0

    for row in view_rows:
        row_count += 1
        logger.info("now on rows = %i of %i, id %s" % (row_count, total_rows, row.id))
        collection = row.doc
        #pprint(collection)
        if collection.has_key("item_tiids"):
            del collection["item_tiids"]
            db.save(collection)
            logger.info("saving")



"""
function(doc) {
    emit([doc.type, doc._id], doc);
}
"""
def put_snaps_in_items():
    logger.debug("running put_snaps_in_items() now.")
    starttime = time.time()
    view_name = "queues/by_type_and_id"
    view_rows = db.view(view_name, include_docs=True)
    row_count = 0
    page_size = 500

    start_key = ["metric_snap", "000000000"]
    end_key = ["metric_snap", "zzzzzzzzzzzzzzzzzzzzzzzz"]

    from couch_paginator import CouchPaginator
    page = CouchPaginator(db, view_name, page_size, include_docs=True, start_key=start_key, end_key=end_key)

    #for row in view_rows[startkey:endkey]:
    while page.has_next:
        for row in page:
            if not "metric_snap" in row.key[0]:
                #print "not a metric_snap so skipping", row.key
                continue
            #print row.key
            row_count += 1
            snap = row.doc
            item = db.get(snap["tiid"])

            if item:
                saving = True
                while saving:
                    try:
                        from totalimpact.models import ItemFactory
                        updated_item = ItemFactory.add_snap_data(item, snap)

                        # to decide the proper last modified date
                        snap_last_modified = snap["created"]
                        item_last_modified = item["last_modified"]
                        updated_item["last_modified"] = max(snap_last_modified, item_last_modified)
                        
                        logger.info("now on snap row %i, saving item %s back to db, deleting snap %s" % 
                            (row_count, updated_item["_id"], snap["_id"]))

                        db.save(updated_item)
                        db.delete(snap)
                        saving = False
                    except couchdb.http.ResourceConflict:
                        logger.warning("couch conflict.  trying again")
                        pass
            else:
                logger.warning("now on snap row %i, couldn't get item %s for snap %s" % 
                    (row_count, snap["tiid"], snap["_id"]))

        page = CouchPaginator(db, view_name, page_size, start_key=page.next, end_key=end_key, include_docs=True)

    logger.info("updated {rows} rows in {elapsed} seconds".format(
        rows=row_count, elapsed=round(time.time() - starttime)
    ))


"""
function(doc) {
    emit([doc.type, doc._id], doc);
}
"""
def ensure_all_metric_values_are_ints():
    #except F1000 Yes's
    view_name = "queues/by_type_and_id"
    view_rows = db.view(view_name, include_docs=True)
    row_count = 0
    page_size = 500

    start_key = ["item", "000000000"]
    end_key = ["item", "zzzzzzzzzzzzzzzzzzzzzzzz"]

    from couch_paginator import CouchPaginator
    page = CouchPaginator(db, view_name, page_size, include_docs=True, start_key=start_key, end_key=end_key)

    #for row in view_rows[startkey:endkey]:
    while page.has_next:
        for row in page:
            row_count += 1
            item = row.doc
            save_me = False
            try:
                metric_names = item["metrics"].keys()
                for metric_name in metric_names:
                    raw = item["metrics"][metric_name]["values"]["raw"]
                    if "scopus:citation" in metric_name:
                        logger.info(item["metrics"][metric_name])
                    if isinstance(raw, basestring):
                        if raw != "Yes":
                            logger.info("casting to int")
                            #logger.info(item)
                            item["metrics"][metric_name]["values"]["raw"] = int(raw)
                            raw = int(raw)
                            save_me=True
                    if not raw:
                        logger.info("removing a zero")
                        #logger.info(item)
                        del item["metrics"][metric_name]
                        save_me=True
                if save_me:
                    logger.info("saving")
                    db.save(item)
                else:
                    #logger.info("%i." %row_count)
                    pass
            except KeyError:
                pass
        logger.info("%i. getting new page" %row_count)
        page = CouchPaginator(db, view_name, page_size, start_key=page.next, end_key=end_key, include_docs=True)


if (cloudant_db == "ti"):
    print "\n\nTHIS MAY BE THE PRODUCTION DATABASE!!!"
else:
    print "\n\nThis doesn't appear to be the production database"
confirm = None
confirm = raw_input("\nType YES if you are sure you want to run this test:")
if confirm=="YES":
    ### call the function here
    ensure_all_metric_values_are_ints()
else:
    print "nevermind, then."

