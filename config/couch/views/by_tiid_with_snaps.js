function(doc) {
	if (doc.type == "item") {
		emit([doc._id, 0], doc);
	} else if (doc.type == "metric_snap") {
		emit([doc.tiid, 1], doc);
	}
}