function(doc){
    if (doc.type == "user") {
        emit (doc.username, null)
    }
}