function(doc) {
    // for items that have aliases, lists items sorted by provider, last request
    //    time, and last update time


    getMetricLastUpdated = function(metricValues){
        latest_key = null
        for (key in metricValues) {
            latest_key = Math.max(latest_key, key)
        }
        return latest_key
    }

    if (typeof doc.metrics == "object" ) {


        // make a list of all the Provider names. We have to be a little hacky
        // because we only store metric names, which *contain* provider names
        // in the form "provider:metric"
        var providerNames = {}
        for (var metricName in doc.metrics) {
            var thisMetric = doc.metrics[metricName]
            if ( !thisMetric.ignore ) {
                var providerName = metricName.split(':')[0]
                lastModified = getMetricLastUpdated(thisMetric.values)

                // overwrite already-entered providers, if we have 'em
                providerNames[providerName] = lastModified
            }
        }

        // now that we've got the provider names, just emit 'em
        for (var name in providerNames) {
            lastModified = providerNames[name]
            emit([name, doc.last_requested, lastModified], doc);

        }
    }
}
