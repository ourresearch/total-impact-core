function(doc) {
    if ( doc.metrics != "undefined") {
        for (var metric in doc.metrics.meta) {
            var item = doc.metrics.meta[metric];
            if ( !item.ignore ) {
                emit([metric,item.last_requested,item.last_modified], doc);
            }
        }
    }
}
