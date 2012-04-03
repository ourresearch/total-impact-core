function(doc) {
    // lists items, ordered by the last-modified time of their aliases.
    if (typeof doc.aliases != "undefined") {
        if (typeof doc.last_modified != "undefined") {
            emit([doc.last_modified], doc.aliases);
        }
    }
}
