function(doc) {
  if (doc.type=="collection") {
    if (doc.alias_tiids) {
	if (doc.last_modified > "2013-06-16") {
	    var numberProducts = Object.keys(doc.alias_tiids).length
            emit(numberProducts, doc._id)
        }
    }
  }
}

// then use reduce function _count

