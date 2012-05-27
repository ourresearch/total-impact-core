function(doc) {
  if (typeof doc.aliases != "undefined") {
    emit([doc._id, 0], doc);
  } else if (typeof doc.drilldown_url != "undefined") {
    emit([doc.tiid, 1], doc);
  }
}