function(doc) {
    // lists items, ordered by the last-queued time of their aliases.
    if (doc.type == "item") {
        if (typeof doc.needs_aliases != "undefined") {
            emit(doc.needs_aliases, doc);
        } 
    }
}
