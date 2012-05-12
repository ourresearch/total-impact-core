import time, re, urllib
from provider import Provider 
from provider import ProviderError, ProviderTimeout, ProviderServerError
from provider import ProviderClientError, ProviderHttpError, ProviderContentMalformedError

from totalimpact.models import Aliases
from BeautifulSoup import BeautifulStoneSoup
import requests
import simplejson
import json

import logging
logger = logging.getLogger('providers.github')

class Github(Provider):  

    metric_names = ['github:watchers', 'github:forks']

    metric_namespaces = ["github"]
    alias_namespaces = ["github"]
    biblio_namespaces = ["github"]

    member_types = ['github_user']

    provides_members = True
    provides_aliases = True
    provides_metrics = True
    provides_biblio = True

    member_items_url_template = "https://api.github.com/users/%s/repos"
    biblio_url_template = "https://github.com/api/v2/json/repos/show/%s"
    aliases_url_template = "https://github.com/api/v2/json/repos/show/%s"
    metrics_url_template = "https://github.com/api/v2/json/repos/show/%s"

    def __init__(self, config):
        super(Github, self).__init__(config)
        self.id = self.config.id

    def get_github_id(self, aliases):
        matching_id = None
        for alias in aliases:
            if alias:
                (namespace, id) = alias
                if namespace == "github":
                    matching_id = id[0]
        print aliases, matching_id
        return matching_id

    def member_items(self, 
            query_string, 
            query_type, 
            provider_url_template=None):
        if not provider_url_template:
            provider_url_template = self.member_items_url_template

        enc = urllib.quote(query_string)

        url = provider_url_template % enc

        logger.debug("attempting to retrieve member items from " + url)
        
        # try to get a response from the data provider        
        response = self.http_get(url, timeout=5)
        if response.status_code != 200:
            raise ProviderServerError(response)

        try:
            hits = simplejson.loads(response.text)
        except simplejson.JSONDecodeError, e:
            raise ProviderContentMalformedError
        hits = [hit["name"] for hit in hits]

        return [("github", (query_string, hit)) for hit in list(set(hits))]

    def biblio(self, 
            aliases,             
            provider_url_template=None):

        if not provider_url_template:
            provider_url_template = self.biblio_url_template

        id = self.get_github_id(aliases)

        if not id:
            logger.info("Not checking biblio as no github id")
            return None

        url = provider_url_template % id
        logger.debug("attempting to retrieve biblio from " + url)
        
        # try to get a response from the data provider        
        response = self.http_get(url, timeout=5)
        
        if response.status_code != 200:
            if response.status_code >= 500:
                raise ProviderServerError(response)
            else:
                raise ProviderClientError(response)
        
        try:
            data = simplejson.loads(response.text) 
        except simplejson.JSONDecodeError, e:
            raise ProviderContentMalformedError

        # extract the biblio
        response = {
            'title' : data['repository']['name'],
            'description' : data['repository']['description'],
            'owner' : data['repository']['owner'],
            'url' : data['repository']['url'],
            'last_push_date' : data['repository']['pushed_at'],
            'create_date' : data['repository']['created_at']
        }

        logger.debug(response)

        return response        

    def aliases(self, 
            aliases, 
            provider_url_template=None):

        if not provider_url_template:
            provider_url_template = self.aliases_url_template

        id = self.get_github_id(aliases)

        url = provider_url_template % id

        logger.debug("hi heather attempting to retrieve aliases from " + url)

        # try to get a response from the data provider        
        response = self.http_get(url)

        logger.debug(response.status_code)
        logger.debug(response.text)
        
        if response.status_code != 200:
            if response.status_code >= 500:
                raise ProviderServerError(response)
            else:
                raise ProviderClientError(response)

        # did we get a page back that seems mostly valid?
        if ("repository" not in response.text):
            raise ProviderContentMalformedError("Content does not contain expected text")

        try:
            data = simplejson.loads(response.text) 
        except simplejson.JSONDecodeError, e:
            raise ProviderContentMalformedError
        
        # extract the aliases
        response = [("github", id), 
                    ("url", data['repository']['url']), 
                    ("title", data['repository']['name'])]

        logger.debug(response)

        logger.debug(id + ": found new aliases: " + str(response))
        return response


    def metrics(self, 
            aliases, 
            provider_url_template=None):

        if not provider_url_template:
            provider_url_template = self.metrics_url_template

        id = self.get_github_id(aliases)

        url = provider_url_template % id

        logger.debug("attempting to retrieve metrics from " + url)
        logger.debug("looking for mentions of github alias %s" % id)

        response = self.http_get(url)

        if response.status_code != 200:
            raise ProviderServerError(response)

        try:
            data = simplejson.loads(response.text) 
        except simplejson.JSONDecodeError, e:
            raise ProviderContentMalformedError

        metrics_response = {
            'github:watchers' : data['repository']['watchers'],
            'github:forks' : data['repository']['forks']
        }

        return metrics_response

