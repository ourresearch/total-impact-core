function(doc) {
    // lists items, ordered by the last-modified time of their aliases.
    if (typeof doc.last_requested != "undefined") {
        if (typeof doc.last_queued == "undefined") {
            // Item has never been queued
            emit(doc.last_queued, [doc.id, "x"]);
        } else { 
            // Item has been queued before, but we have re-requested it
            if (doc.last_queued < doc.last_requested) {
                emit(doc.last_requested, [doc.id, doc.last_queued]);
            }
        }
    }
}
