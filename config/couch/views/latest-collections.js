function(doc) {
    if (doc.type == "collection") {
        var test = 0
        if (doc.title.indexOf("[ti test]") == 0) {
            test = 1;
        }
        var ip_address = ""
        if (typeof doc.ip_address != "undefined") {
            ip_address = doc.ip_address
        }
        emit([test, doc.created], [doc.title, doc.item_tiids.length, ip_address])
    }
}