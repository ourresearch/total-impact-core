from totalimpact import views, fakes

""" This file runs the method accessed from the /tests/create_collection endpoint.

It's a hack to get around the fact we use the Flask webserver in local testing;
this webserver can only handle one request at a time. If it's serving the test
request, it can't also server the API requests that the test method makes."""

fake_user = fakes.User()
report = fake_user.do("make_collection")