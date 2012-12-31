function(doc) {
    // lists registered items by current api keys
    if (doc.type == "api_user") {

    	// emit one or more rows for every namespace in aliases
        for (var alias in doc.registered_items) {

           emit([alias, doc.current_key.toLowerCase()], doc.registered_items[alias]["tiid"]);
            
        }
    }
}
