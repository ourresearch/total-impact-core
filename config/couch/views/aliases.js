function(doc) {
    // lists items, ordered by the last-modified time of their aliases.
    if (typeof doc.aliases != "undefined") {
        if (typeof doc.last_requested != "undefined") {
            if (typeof doc.aliases.last_updated == "undefined") {
                // Aliases has never been defined
                emit([doc.last_requested], doc);
            } else { 
                // Aliases has been defined, but it is behind the doc definition
                if (doc.aliases.last_updated < doc.last_requested) {
                    emit([doc.last_requested], doc);
                }
            }
        }
    }
}
