function(doc) {
    if (doc.type == "collection") {
        if (doc.title.indexOf("[refset-test]") == 0) {
           emit(doc.title, 1)
        }
    }
}