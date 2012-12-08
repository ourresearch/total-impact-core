function(doc) {
    // lists aliases with provider batch data
    if (doc.type == "provider_data_dump") {
        // emit one or more rows for every namespace in aliases
        for (var namespace in doc.aliases) {
            namespaceid_list = doc.aliases[namespace];

            // if just a single value, put it in a list
            if (typeof namespaceid_list == "string") {
                  namespaceid_list = new Array(namespaceid_list);
            }

            // emit a row for every id in the namespace id list except meta
            for (var i in namespaceid_list) {
                var nid = namespaceid_list[i].toLowerCase();                
                emit([doc.provider, [namespace, nid]], doc.max_event_date);
            }
        }
    }
}