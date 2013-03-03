function(doc) {
    if (doc.type == "item") {

    	// use the full published date if available
    	// otherwise use the end of the year it was published (unless that is after we first saw it)
    	// or else just use the date we first saw it

        // use the full published date if available
        // otherwise use the end of the year it was published (unless that is after we first saw it)
        // or else just use the date we first saw it
        var date_published;
        date_published = new Date("1900-01-01T00:01:01.000Z");

        if (typeof doc.created !== "undefined") {
        var date_created = new Date(doc.created);
            date_published = date_created;
            if (typeof doc.biblio !== "undefined") {
                if (typeof doc.biblio.year !== "undefined") {
                    date_published = new Date(doc.biblio.year.toString() + "-12-31T00:01:01.000Z");
            if (isNaN(date_published)) {
            date_published = new Date(doc.created);
            } else if (date_published > date_created) {
            date_published = date_created;
            }
                }            
            }
        }

        if (typeof doc.biblio !== "undefined") {
           if (typeof doc.biblio.date !== "undefined") {
               date_published = new Date(doc.biblio.date);
           } 
        }

        if (date_published == "Invalid Date")  {
            date_published = new Date("1900-01-01T00:01:01.000Z");
        }

        if (isNaN(date_published)) {
            date_published = new Date("1900-01-01T00:01:01.000Z");
        }


    	// use the date the last update ran
    	// otherwise use the date it was last modified, perhaps by a manual update button
    	var date_last_updated;
    	if (typeof doc.last_update_run != "undefined") {
	        date_last_updated = new Date(doc.last_update_run);
    	} else {
    		date_last_updated = new Date(doc.last_modified);
    	}

		var one_day = 1000*60*60*24;
	    var diff_date = date_last_updated - date_published;
		emit([date_last_updated.toISOString(), Math.floor(diff_date/one_day), date_published.toISOString()], doc._id); 
    }
}
