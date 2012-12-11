function(doc) {
    // lists aliases by last_modified
    if (doc.type == "item") {
    	if (typeof doc.last_update_run == "undefined") {
	        emit(doc.last_modified, doc._id)
    	} else {
	        emit(doc.last_update_run, doc._id)
	    }
    }
}
