function(doc) {
    if (doc.type == "collection") {
        var test = 0
        if (doc.title.indexOf("[ti test]") == 0) {
            test = 1;
        }
        emit([test, doc.created], [doc.title, doc.item_tiids.length])
    }
}