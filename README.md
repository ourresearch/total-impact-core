# About

This is the latest version of total-impact-core. Installing this provides the 
backend and API for the total-impact service. You can then build or run a 
frontend or consume direct from the API into your own frontend.

(Our own frontend is available at [http://github.com/total-impact/total-impact-webapp](http://github.com/total-impact/total-impact-webapp).)

This isn't the deployed version -- it is an in-progress port the old codebase 
at http://github.com/mhahnel/Total-Impact

The deployed version is available at [http://total-impact.org](http://total-impact.org), 
and see [http://total-impact.org/about](http://total-impact.org/about) for more info.


# Dependencies

You may need sudo / root privileges, use if necessary

    apt-get install gcc     
    apt-get install python-lxml
    apt-get install memcached
    apt-get install couchdb
    apt-get install python-setuptools


# Install

This assumes you are running on a recent debian / Ubuntu based server.

Get total-impact-core code by cloning from this repo and cd into the directory.
There are various ways to get code from the repo, here is one example.

    apt-get install git
    git clone https://github.com/total-impact/total-impact-core
    cd total-impact-core

You should consider using a virtualenv too, but it is optional.

How to install:

    python setup.py install

Or to install for dev:

    easy_install pip
    pip install -e .

Check CouchDB is available

    # check couch is up
    curl -X GET http://localhost:5984   # or use your web browser


# Config

Total-impact will try to contact CouchDB at http://localhost:5984/ 
When total-impact starts, it will, if necessary, create the database and all necessary views. 


# Running

These will only work if install is successful and the CouchDB is available with proper user auth set up.

How to run the API and check it is up:

    python totalimpact/api.py
    curl -X GET http://127.0.0.1:5001/  # or use your web browser

For dev, how to run tests:

    apt-get install python-nose
    nosetests -v test/
    nosetests -v -A "not slow" test/    # avoids slow tests

Note also that running the API as above is the first stage in making it publicly available.
Follow-up should include checking that debug is set to False, then exposing the API via
a web server such as NGINX. Supervisord is recommended for keeping your processes up. 
There are lots of different ways to do this, so we will not go into detail.


# Notes for Mac

Deal with problems on OSX Snow Leopard:

1. Install [homebrew](http://mxcl.github.com/homebrew/).
2. Run `brew install -v couchdb` (The `-v` for "verbose" fixes a [weird bug](http://code418.com/blog/2012/02/22/couchdb-osx-lion-verbose/)). Install will take a while, as there are big dependencies.
3. Run `couchdb` to start Couch. Done. You can test the CouchDB install at <http://localhost:5984/_utils>


# Writing Providers

Total Impact uses many different data sources to acquire its metrics, and each of these data sources is connected to via a Provider client library which lives in the TI application.

The provider super-class and the individual implementations can be found in the module

    totalimpact.providers
    
The super-class is at:

    totalimpact.providers.provider.Provider
    
Inside the provider module there are also a bunch of other useful things such as a ProviderFactory and a suite of errors that providers can use.

To create a new provider, the first thing to do is sub-class the Provider and insert stubs for the methods which Providers can support

    from totalimpact.providers.provider import Provider
    
    class MyWonderfulProvider(Provider):
        
        def __init__(self, config, app_config):
            super(MyWonderfulProvider, self).__init__(config, app_config)
        
        def provides_metrics(self): 
            return False
        
        def member_items(self, query_string, query_type): 
            raise NotImplementedError()
            
        def aliases(self, item): 
            raise NotImplementedError()
        
        def metrics(self, item):
            raise NotImplementedError()
        
        def biblio(self, item): 
            raise NotImplementedError()

See the API documentation for full details of each of these methods, but here is a brief summary:

* provides_metrics
  Does the provider offer to gather metrics from its data sources?  This is used to determine whether the provider will get its own thread to operate in, so is important to have in addition to the metrics() function
  
* member_items
  Takes an opaque string and query type from the front end and queries the data source for identifiers related to that query.  For example, you may query the data source for a username, and get back a list of the object identifiers for that user.  This is used to seed the construction of collections of objects.
  
* aliases
  Take an item, and acquire all of the aliases that the item could be identified by.  The data source would be queried using any existing identifiers associated with an item, and would acquire more synonymous identifiers.  These should then be attached to the item's alias object (see the Item API documentation)
  
* metrics
  Take an item, and using its internal aliases populate one or more MetricSnap objects and attach them to the item's metrics object (see the Item API documentation)
  
* biblio
  Take an item and using any of the internal data for querying the data source obtain bibliographic data and attach it to the item's biblio object.  (see the Item API documentation)

Each Provider that runs must be declared in the main TI configuration file, so before you can get yours to execute you must update

    config/totalimpact.conf.json
    
and include the classname of your provider and the route to the providers configuration file.  You add it to the "providers" config option, thus:

    "providers" : [
        {
            "class" : "totalimpact.providers.myprovider.MyWonderfulProvider",
            "config" : "totalimpact/providers/myprovider.conf.json"
        },
        ... other providers ...
    ],
    
When the TI application starts, all the providers will be loaded from configuration, and those which return True on provides_metrics() will be given their own worker thread, and will be passed items from the Queue to process the metrics for.  They will also be added to an aliasing worker thread which will pass them items for which to obtain aliases.  There is no need for individual providers to know about threading - they should operate as pure client libraries joining TI to the data source.

It is not possible to provide a generic recipe for constructing a provider, as each data source will have its own idioms and approaches.  Instead, we can describe the features that the super-class has to support the implementation, and the error handling which is implemented in the thread.

In particular, the super-class provides an http_get() method which providers SHOULD and are strongly RECOMMENDED to use when connecting out over HTTP to GET web services.  This provides a wrapped HTTP request which supports cacheing.  So in your provider implementation:

    metrics(self, item):
        url = self._make_url(item)
        response = self.http_get(url)
        ... do stuff with response ...

The returned response object is a "requests" HTTP response object

If errors are thrown by any part of the provider, they should be wrapped or expressed using one of the appropriate error classes:

* ProviderConfigurationError
  if the provider's supplied configuration is incorrect, this error may be thrown.  Extends the ProviderError class, and may take a human readable message and/or an inner exception
  
    raise ProviderConfigurationError("configuration did not parse")
    
* ProviderTimeout
  raised on the provider's behalf by the http_get() method, if the HTTP request times out
  
* ProviderHttpError
  raised on the provider's behalf by the http_get() method, if the HTTP response is technically incorrect
    
* ProviderClientError
  Should be raised when the client experiences an HTTP error which was its own fault.  Typically this is when HTTP status codes in the range 400-499 are returned, although exactly when this error is thrown is left to the discretion of the Provider implementation.  It MUST take a response object as an argument in the constructor, and may also take an error message and inner exception
  
    response = self.http_get(url)
    if response.status_code >= 400 and response.status_code < 500:
        raise ProviderClientError(response, "my fault!")

* ProviderServerError
  Should be raised when the client experiences an HTTP error which was the server's fault.  Typically this is when HTTP status codes in the range 500+ are returned, although exactly when this error is thrown is left to the discretion of the Provider implementation.  It MUST take a response object as an argument in the constructor, and may also take an error message and inner exception
  
    response = self.http_get(url)
    if response.status_code > 500:
        raise ProviderServerError(response, "server's fault!")
    
* ProviderContentMalformedError
  Should be raised when the client is unable to parse the document retrieved from the data source (e.g. malformed XML, JSON, etc).  Extends the ProviderError class, and may take a human readable message and/or an inner exception
  
    raise ProviderContentMalformedError("was not valid XML")

* ProviderValidationFailedError
  Should be raised when the client is unable to validate the successfully parsed document as the document it was expecting.  This could happen if, for example, the response from the data source has changed structure (e.g. new XML schema) without the provider being aware of the change.  Extends the ProviderError class, and may take a human readable message and/or an inner exception
  
    raise ProviderValidationFailedError("couldn't find the result element")

If a provider experiences an error, the supervising thread will consider the options and may re-try requests, in order to mitigate against errors like network blips or known weaknesses in data sources.  The Provider is responsible for providing the supervising thread the information it needs to make those decisions, which it does be declaring in its own configuration file the following block:

    "errors" : {
        "timeout" : { 
            "retries" : 0, "retry_delay" : 0, 
            "retry_type" : "linear", "delay_cap" : -1 },
        "http_error" : { 
            "retries" : 0, "retry_delay" : 0, 
            "retry_type" : "linear", "delay_cap" : -1 },
        "client_server_error" : { 
            "retries" : 0, "retry_delay" : 0, 
            "retry_type" : "linear", "delay_cap" : -1 },
        "rate_limit_reached" : { 
            "retries" : -1, "retry_delay" : 1, 
            "retry_type" : "incremental_back_off", "delay_cap" : 256 },
        "content_malformed" : { 
            "retries" : 0, "retry_delay" : 0, 
            "retry_type" : "linear", "delay_cap" : -1 },
        "validation_failed" : { 
            "retries" : 0, "retry_delay" : 0, 
            "retry_type" : "linear", "delay_cap" : -1}
    },

This is retrieved by the supervising thread during an exception, and used to make decisions as to the re-try strategy.  Each exception corresponds to one of the error keys (e.g. ProviderTimeout -> "timeout")

CONTINUE ...
