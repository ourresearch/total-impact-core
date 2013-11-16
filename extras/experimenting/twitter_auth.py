from birdy.twitter import AppClient
from requests.auth import HTTPBasicAuth
from requests_oauthlib import OAuth1Session, OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient
import requests
import json

import os

TWITTER_API_VERSION = '1.1'
TWITTER_BASE_API_URL = 'https://api.twitter.com'

api_version=TWITTER_API_VERSION
base_api_url=TWITTER_BASE_API_URL

consumer_key=os.getenv("TWITTER_CONSUMER_KEY")
print consumer_key
consumer_secret = os.getenv("TWITTER_CONSUMER_SECRET")
print consumer_secret
access_token = os.getenv("TWITTER_ACCESS_TOKEN")
print access_token

request_token_url = '%s/oauth2/token' % base_api_url

auth = HTTPBasicAuth(consumer_key, consumer_secret)

client = BackendApplicationClient(consumer_key)

token = {'access_token': access_token, 'token_type': "bearer" }

session = OAuth2Session(client=client, token=token)

print session.verify
print session.token

a = session.get("https://api.twitter.com/1.1/users/show.json?screen_name=researchremix")

print a
print a.text


# data = {'grant_type': 'client_credentials'}

# response = session.post(request_token_url, auth=auth, data=data)
# print response

# data = json.loads(response.content.decode('utf-8'))
# print data
# access_token = data['access_token']


# temp_client = AppClient(os.getenv("TWITTER_CONSUMER_KEY"), 
#                     os.getenv("TWITTER_CONSUMER_SECRET"))

# access_token = temp_client.get_access_token()

# print "generated access token", access_token, os.getenv("TWITTER_ACCESS_TOKEN")

# client = AppClient(os.getenv("TWITTER_CONSUMER_KEY"), 
#                     os.getenv("TWITTER_CONSUMER_SECRET"),
#                     os.getenv("TWITTER_ACCESS_TOKEN"))
