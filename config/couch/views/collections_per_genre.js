function(doc) {
  if (doc.type=="collection") {
    var proxies = [":", "doi", "pmid", "biblio", "github", "figshare", "dryad", "slideshare", "url", "article"]
    var found_one = {}
    for (var proxy in proxies) {
      found_one[proxies[proxy]] = 0
    }
    if (doc.alias_tiids) {
	if (doc.last_modified > "2013-06-16") {
	    for (var alias in doc.alias_tiids) {
                var lowerCaseAlias = alias.toLowerCase()
		for (var proxy in proxies) {
                   if (lowerCaseAlias.indexOf(proxies[proxy]) >= 0) {
                      found_one[proxies[proxy]] = 1
                   }
                }
            }
            if (found_one["pmid"] || found_one["doi"] || found_one["biblio"]) {
                found_one["article"] = 1
            } else {
                found_one["article"] = 0
            }
            for (var proxy in proxies) {
                if (found_one[proxies[proxy]] > 0) {
                   emit(proxies[proxy], doc._id)
                }
            }
        }
    }
  }
}

// then use reduce function _count

