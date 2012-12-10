function(doc) {
    // lists aliases by last_modified
    if (doc.type == "item") {
        emit(doc.last_modified, doc._id)
    }
}
