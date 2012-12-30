function(doc) {
    // lists docs by current api keys
    if (doc.type == "api_user") {
        emit([doc.current_key], [doc.created]);
    }
}
