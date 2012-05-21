
# Writing Providers

Total Impact uses many different data sources to acquire its metrics, and each of 
these data sources is connected to via a Provider client library which lives in the TI application.

The provider super-class and the individual implementations can be found in the module

    totalimpact.providers
    
The super-class is at:

    totalimpact.providers.provider.Provider
    
Inside the provider module there are also a bunch of other useful things such as a ProviderFactory 
and a suite of errors that providers can use.

To create a new provider, the first thing to do is sub-class the Provider and define attributes
which state what functionality the provide supports. 

    from totalimpact.providers.provider import Provider

    class NewProvider(Provider):  


The x_namespaces and x_name attributes are filters. These will ensure that your provider isn't passed
any data which it cannot deal with. These will be explained shortly.
    
Now add in member functions which provide the core functionality of the provider you are creating.
If your provider doesn't support a particular method, just leave it undefined and set the provides_x
attribute appropriately.

        def member_items(self, query_string, query_type): 
        def aliases(self, aliases): 
        def metrics(self, aliases):
        def biblio(self, aliases): 

See the API documentation for full details of each of these methods, but here is a brief summary:

* member_items

Takes an opaque string and query type from the front end and queries the data source for identifiers 
related to that query.  For example, you may query the data source for a username, and get back a 
list of the object identifiers for that user.  This is used to seed the construction of collections 
of objects.
  
* aliases

Take a list of aliases and return back a list of all related aliases that this provider can find.
The aliases list is in the form of a list of tuples of type (namespace, id) for example 
[('doi', '10.5061/dryad.7898'), ('url','http://datadryad.org/handle/10255/dryad.7898')]
This method should return an aliases list in the same format, which may or may not include the 
originally supplied aliases. Duplicate aliases will be removed by the backend code to prevent
loops.

The supplied list of aliases will only contain aliases in the namespaces which were defined in
alias_namespaces

* metrics

This method is supplied a list of aliases for which to obtain metric information. The supplied 
aliases are in the same format as supplied to the aliases method. The supplied list of aliases 
will only contain aliases in the namespaces which were defined in metric_namespaces

Multiple aliases for the same item can be used to remove duplicate references. For example, a 
document which both has a DOI and URL alias may show up in search for both of those aliases. If
we searched for each alias on the remote server and combined results, we could be including 
duplicates. Providing all aliases allows the metrics method to perform an 'OR' query on the remote
server to remove duplicates.

The metrics method should return a dictionary, providing the values for each metric defined in
metric_names.

    {
      "github:forks": 1,
      "github:followers": 7
    }

Should a single metric not exist for an item, you should return a None value for the metric. If
no metrics exist all, you can return None instead of a dict.

Some providers will never deal with more than a single alias at any time, due to the nature
of the provider. For example, the wikipedia provider only expects a single DOI entry. In this
case, simply read the first item, and if multiple are passed log a warning in the logs.

    def metrics(self, aliases):
        if len(aliases) != 1:
            logger.warn("More than 1 DOI alias found, this should not happen. Will process first item only.")
  
  
* biblio

This method is supplied a list of aliases for which to obtain bibliographic information. The supplied 
aliases are in the same format as supplied to the aliases method. The supplied list of aliases 
will only contain aliases in the namespaces which were defined in biblio_namespaces

This method should return a dict
FIXME: What is this?


## Configuration 

Each Provider that runs must be declared in the main TI configuration file, so before you can get yours to execute you must update

    config/totalimpact.conf.json
    
and include the classname of your provider and the route to the providers configuration file.  You add it to the "providers" config option, thus:

    "providers" : [
        {
            "class" : "totalimpact.providers.newprovider.NewProvider",
            "config" : "totalimpact/providers/newprovider.conf.json"
        },
        ... other providers ...
    ],
    
When the TI application starts, all the providers will be loaded from configuration, and those which have 
provides_metrics defined as true will be given their own worker threads, and will be passed items from the 
Queue to process the metrics for. The application will also create aliasing worker threads which will pass 
them items for which to obtain aliases. 

There is no need for individual providers to know about threading - they should operate as pure client 
libraries joining TI to the data source. Similarly, error handling and dealing with retries is mostly
performed by the application, not by the providers themselves.

It is not possible to provide a generic recipe for constructing a provider, as each data source will 
have its own idioms and approaches.  Instead, we can describe the features that the super-class has to 
support the implementation, and the error handling which is implemented in the thread.

In particular, the super-class provides an http_get() method which providers MUST use when connecting 
out over HTTP to GET web services. This provides a wrapped HTTP request which supports cacheing and 
handles failures and timeouts correctly.  So in your provider implementation:

    metrics(self, item):
        url = self._make_url(item)
        response = self.http_get(url)
        ... do stuff with response ...

The returned response object is a "requests" HTTP response object.
FIXME: Link to requests library

If errors are thrown by any part of the provider, they should be wrapped or expressed using one of the 
appropriate error classes:

* ProviderConfigurationError

If the provider's supplied configuration is incorrect, this error may be thrown. Extends the 
ProviderError class, and may take a human readable message and/or an inner exception
  
    raise ProviderConfigurationError("configuration did not parse")
    
* ProviderTimeout

Raised on the provider's behalf by the http_get() method, if the HTTP request times out.
  
* ProviderHttpError

Raised on the provider's behalf by the http_get() method, if there are problems making the
HTTP connection. Error codes such as 4xx or 5xx from the remote server will not raise this
error, intead do_get will return back a "requests" object with the error code set. 
    
* ProviderClientError

Should be raised when the client experiences an HTTP error which was its own fault. Typically 
this is when HTTP status codes in the range 400-499 are returned, although exactly when this 
error is thrown is left to the discretion of the Provider implementation.  It MUST take a 
response object as an argument in the constructor, and may also take an error message 
and inner exception
  
    response = self.http_get(url)
    if response.status_code >= 400 and response.status_code < 500:
        raise ProviderClientError(response, "my fault!")

* ProviderServerError

Should be raised when the client experiences an HTTP error which was the server's fault.  
Typically this is when HTTP status codes in the range 500+ are returned, although exactly 
when this error is thrown is left to the discretion of the Provider implementation.  
It MUST take a response object as an argument in the constructor, and may also take an 
error message and inner exception
  
    response = self.http_get(url)
    if response.status_code > 500:
        raise ProviderServerError(response, "server's fault!")
    
* ProviderContentMalformedError

Should be raised when the client is unable to parse the document retrieved from the data 
source (e.g. malformed XML, JSON, etc). Extends the ProviderError class, and may take a 
human readable message and/or an inner exception
  
    raise ProviderContentMalformedError("was not valid XML")

* ProviderValidationFailedError

Should be raised when the client is unable to validate the successfully parsed document 
as the document it was expecting.  This could happen if, for example, the response from 
the data source has changed structure (e.g. new XML schema) without the provider being 
aware of the change.  Extends the ProviderError class, and may take a human readable 
message and/or an inner exception
  
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

This is retrieved by the supervising thread during an exception, and used to make decisions 
as to the re-try strategy.  Each exception corresponds to one of the error keys 
(e.g. ProviderTimeout -> "timeout")


## Setting up test data

As providers will deal with external datasources and normally require a number of http
requests in sequence, it's very beneficial to use both tests and test data to develop them.
You may want to start with doing this before you write your provider.

Use curl to download html data to use as new test data items. You will want to create
examples for each category of item you process, so that your tests can cover all major
code-paths and cases

    curl -o out.xml http://api.service.com/v1/item-info?format=xml&itemid=129485
    mv out.xml test/data/new_provider/example_item1.xml 

Note that all tests that you write should be written using pre-recorded http responses. If
the test suite makes http connections to live services when it's run, it risks failing 
unexpectedly due to the third party service failing.


## Writing test cases

Now create a test case for your new provider, using the following template

    class TestNewProvider(ProviderTestCase):

        testitem_members = None
        testitem_aliases = ("doi", TEST_WIKIPEDIA_DOI)
        testitem_metrics = ("doi", TEST_WIKIPEDIA_DOI)
        testitem_biblio = ("doi", TEST_WIKIPEDIA_DOI)

        provider_name = 'NewProvider'

        def setUp(self):
            ProviderTestCase.setUp(self)

The testitem_* methods should be provided with an identifier of a valid item
for each of those methods. If the methods aren't implmented, just set this
to None.

The ProviderTestCase class will provide a number of standard tests to 
ensure your provider is fully implemented and handles error cases correctly.
You will want to pay attention to:

    def test_provider_aliases_400(self):
    def test_provider_aliases_500(self):
    def test_provider_aliases_empty(self):
    def test_provider_aliases_nonsense_txt(self):
    def test_provider_aliases_nonsense_xml(self):

These methods will call aliases, having modified the http_get method
to return the relvant data for testing. Similar tests exist for the 
metrics, member_items and biblio methods.

If you don't want to use these tests, or want to extend them, simply
override the various methods in your own test case class.

You can now extend the TestNewProvider class you have just created to 
add in your own tests to deal with the specific logic for the provider
you are using.

To use the test data you downloaded earlier in your tests, define your
data items at the top of your test case code file.

    from test.provider import DummyResponse
    datadir = os.path.join(os.path.split(__file__)[0], "../../data/new_provider")
    TEST_ITEM1 = os.path.join(datadir, "example_item1.xml")

Now in your test, replace the http_get method to simulate the responses you want

    def test_some_aspect(self):
        f = open(TEST_ITEM1, "r")
        self.http_get = lambda: DummyResponse(200, f.read())

You don't need to clean up http_get at the end of your test, the base class already
handles preserving this method between tests for you.

For more complex scenarios, you may need to replace http_get with a function
which returns different responses for different URLs. This would then let you
simulate failures at different points in a sequence.


## Using the test proxy 

The providers_test_proxy.py is provided to allow you to develop on code without needing the system
to contact external services. This reduces any unncessary load on external services (and potential 
blocking or blacklisting of your connection) and also ensures that responses you are dealing with 
are consitent during your development.

To use the test proxy, set your PROXY variable in detault_settings.py or create your own local
config file which overrides default_settings.py

    PROXY = "http://localhost:8081"

Now start the test proxy in a different terminal window

    ./extras/providers_test_proxy.py -p 8081

Viewing the log file in logs/proxy.log will show you what requests are made to external services
and are subsequently answered by the canned responses, service from the test/data directoy. If
a URL is requested which the proxy doesn't know about, it will print 'Not found' in the logs and
return an error.

To add new entries to the test proxy, download the data using curl and demonstrated earlier. Add 
this test data to the providers_test_proxy.py script, by creating new entries similar to the following

    responses['new_provider']['metrics_item1'] = load_test_data('new_provider', 'example_item1.xml')

    urlmap = {
        ...
        "http://api.service.com/v1/item-info?format=xml&itemid=129485": responses['new_provider']['metrics_item1'],
        ...
    }

Restart the test proxy, and it should now start replaying the HTTP response you recorded when the
relevant URL is accessed by your provider. 

If you want to run the test proxy as a daemon process and leave it running persistently, you can
use the -d flag to tell it to daemonize

    ./extras/providers_test_proxy.py -d -p 8081

This will log output in the logs/ directory, and store it's PID into proxy.pid in the total 
impact directory. To stop the daemon running, use

    kill `cat proxy.pid`
