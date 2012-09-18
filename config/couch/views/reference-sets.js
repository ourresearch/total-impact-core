function(doc) {
    if (doc.type == "collection") {
        if (typeof doc["refset_metadata"] != "undefined") {
           emit([doc._id, doc.title], doc["refset_metadata"])
        }
    }
}