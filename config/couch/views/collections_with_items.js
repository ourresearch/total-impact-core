function(doc) {
  if (doc.type=="collection") {
    emit([doc._id, 0], null);
    if (doc.alias_tiids) {
      for (var alias in doc.alias_tiids) {
	var item_id = doc.alias_tiids[alias]
        emit([doc._id, item_id], {_id: item_id});
      }
    }
  }
}