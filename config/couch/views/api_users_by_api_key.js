function(doc) {
    // lists docs by api keys
    if (doc.type == "api_user") {
        emit([doc.current_key], 1);
    }
}
