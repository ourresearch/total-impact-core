function(doc) {
    // lists aliases by last_modified
    if (doc.type == "item") {
	    if (typeof doc.aliases.doi != "undefined") {
	    	var doi = doc.aliases.doi[0]
			if (typeof doi.slice(3).indexOf(".") != "undefined") {
		    	var index_of_first_period_after_prefix = 3 + doi.slice(3).indexOf(".")
		    	var doi_prefix = doi.slice(0, index_of_first_period_after_prefix)
		    	if (typeof doc.last_update_run == "undefined") {
			        emit([doi_prefix, doc.last_modified], doc._id)
		    	} else {
			        emit([doi_prefix, doc.last_update_run], doc._id)
			    }
			}
	    }
	}
}
