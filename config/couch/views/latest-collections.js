function(doc) {
    if (doc.type == "collection") {
        var is_test = 0
        if (doc.title.indexOf("[ti test]") == 0) {
            is_test = 1;
        }
        var ip_address = ""
        if (typeof doc.ip_address != "undefined") {
            ip_address = doc.ip_address
        }
        var num_tiids = 0;
        for(var p in doc.alias_tiids){
            ++num_tiids;
        }
        emit([is_test, doc.created], [doc.title, num_tiids, ip_address])
    }
}
