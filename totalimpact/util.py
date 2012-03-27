from functools import wraps
from flask import request, current_app


# a slow decorator for tests, so can exclude them when necessary
# put @slow on its own line above a slow test method
# to exclude slow tests, run like this: nosetests -A "not slow"
def slow(f):
    f.slow = True
    return f

# derived from the jsonp function in bibserver
def jsonp(f):
    """Wraps JSONified output for JSONP"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        callback = request.args.get('callback', False)
        if callback:
            content = str(callback) + '(' + str(f(*args,**kwargs).data) + ')'
            return current_app.response_class(content, mimetype='application/javascript')
        else:
            return f(*args, **kwargs)
    return decorated_function


# derived from http://flask.pocoo.org/snippets/45/ (pd) and customised
# should be replaced with negotiator
def request_wants_json():
    best = request.accept_mimetypes \
        .best_match(['application/json', 'text/html'])
    best == 'application/json' and \
        request.accept_mimetypes[best] > \
        request.accept_mimetypes['text/html']
    if request.values.get('format','').lower() == 'json' or request.url().endswith(".json"):
        best = True
    return best

