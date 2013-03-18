function(doc) {
    if (doc.type == "item") {

        // determine the published date using biblio if it contains a full published date
        // if full date is unavailable, use Dec 31st of the year it was published, 
        //    unless that is later than the first time we saw it
        // if that fails, just use the date we first saw it as the published date
        // if everything fails, use a date before computers were invented.
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


        // to determine the last updated date, use the last update run date if it has one
        // otherwise use the date it was last modified, perhaps by a manual update button
        var date_last_updated;
        if (typeof doc.last_update_run != "undefined") {
            date_last_updated = new Date(doc.last_update_run);
        } else {
            date_last_updated = new Date(doc.last_modified);
        }


        //  group "A" is for papers older than 2012.  update yearly.
        //  group "B" is for papers published in 2012.  update monthly.
        //  group "C" is for papers published after 2013.  
        //    update these weekly or daily, depending on days since published
        //    so we need to export details on month and date published
        var year_published = date_published.getFullYear()
        var group;        
        var month_group;
        if (year_published < 2012) {
            group = "A";
            month_group = 0;
        } else if (year_published < 2013) {
            group = "B";
            month_group = 0;
        } else {
            group = "C";
            month_group = date_published.getMonth() + 1;  // so that starts at 1
        }

        emit([group, month_group, date_last_updated.toISOString(), date_published.toISOString()], doc._id); 
    }
}

