#!/usr/bin/env python

import logging, couchdb, os
from totalimpact import dao, tiredis
from totalimpact.models import ItemFactory

logger = logging.getLogger('ti.updater')
logger.setLevel(logging.DEBUG)


"""
function(doc) {
    // lists tiids by individual alias namespaces and ids
    if (doc.type == "item") {
        // expecting every alias object has a tiid
        tiid = doc["_id"];

        // emit one or more rows for every namespace in aliases
        for (var namespace in doc.aliases) {

            // don't emit meta info
            if ((namespace == "created") || (namespace == "last_modified")) {
                continue
            }

            // otherwise continue
            namespaceid_list = doc.aliases[namespace];

            // if just a single value, put it in a list
            if (typeof namespaceid_list == "string") {
                  namespaceid_list = new Array(namespaceid_list);
            }

            // emit a row for every id in the namespace id list except meta
            for (var i in namespaceid_list) {
                emit([namespace, namespaceid_list[i]], tiid);
            }
        }
    }
}
"""
def get_elife_dois(mydao):
    db = mydao.db
    dois = []
    view_name = "queues/by_alias"
    view_rows = db.view(view_name, 
            include_docs=False, 
            startkey=["doi", "10.7554/eLife.0000000000"], 
            endkey=["doi", "10.7554/eLife.zzzzzzzzzz"])
    row_count = 0

    for row in view_rows:
        row_count += 1
        doi = row.key[1]
        dois += [doi]
        #logger.info("\n%s" % (doi))
    return dois

def update_elife_dois(myredis, mydao):
    dois = get_elife_dois(mydao)
    aliases = [("doi", doi) for doi in dois]
    tiids = ItemFactory.create_or_update_items_from_aliases(aliases, myredis, mydao)
    return tiids

def main():
    cloudant_db = os.getenv("CLOUDANT_DB")
    cloudant_url = os.getenv("CLOUDANT_URL")

    #cloudant_db = "ti"
    #cloudant_url = "https://app5109761.heroku:TuLL8oXFh4k0iAcAPnDMlSjC@app5109761.heroku.cloudant.com"

    #cloudant_db = "staging-ti2"
    #cloudant_url = "https://app5492954.heroku:Tkvx8JlwIoNkCJcnTscpKcRl@app5492954.heroku.cloudant.com"

    mydao = dao.Dao(cloudant_url, cloudant_db)
    myredis = tiredis.from_url(os.getenv("REDISTOGO_URL"))

    try:
        tiids = create_and_update_elife_dois(myredis, mydao)
        print tiids
    except (KeyboardInterrupt, SystemExit): 
        # this approach is per http://stackoverflow.com/questions/2564137/python-how-to-terminate-a-thread-when-main-program-ends
        sys.exit()
 
if __name__ == "__main__":
    main()
