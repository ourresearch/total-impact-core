import requests, iso8601, os, json, logging
import urllib2
import base64
import time
import urlparse

logger = logging.getLogger("ti.mixpanel")

def track(event, event_properties, flask_request=None, mixpanel_token=None):
    logger.debug("**** MIXPANEL LOG********")

    if not mixpanel_token:
        mixpanel_token = os.getenv("MIXPANEL_TOKEN")

    properties = {
        'token': mixpanel_token, 
        'time': int(time.time())
        }

    if flask_request:
        properties.update({  
            'ip': flask_request.remote_addr,
            "$referrer" : flask_request.referrer,
            "$os": flask_request.user_agent.platform,
            "$browser": flask_request.user_agent.browser
            })
        try:
            properties["$referring_domain"] = urlparse.urlsplit(flask_request.referrer).netloc
        except AttributeError:
            pass

    properties.update(event_properties)

    mixpanel_data = base64.b64encode(json.dumps({"event": event, "properties": properties}))
    url = "http://api.mixpanel.com/track/?data=%s" % mixpanel_data
    logger.debug(url)
    mixpanel_resp = urllib2.urlopen(url)
    logger.debug(mixpanel_resp)

    logger.debug("Successful mixpanel report")
    return