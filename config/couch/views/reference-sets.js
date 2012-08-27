function(doc) {
    if (doc.type == "collection") {
        if (doc.title.indexOf("[reference-set]") == 0) {
           emit(doc.title, 1)
        }
    }
}