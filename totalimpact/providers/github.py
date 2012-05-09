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

    provider_name = "github"
    metric_names = ['github:watchers', 'github:forks']

    metric_namespaces = ["github"]
    alias_namespaces = ["github"]
    biblio_namespaces = ["github"]

    member_types = ['github_user']

    provides_members = True
    provides_aliases = True
    provides_metrics = True
    provides_biblio = True

    def __init__(self, config):
        super(Github, self).__init__(config)
        self.id = self.config.id

    def get_github_id(self, aliases):
        matching_id = [id for (namespace, id) in aliases if namespace=="github"]
        if matching_id:
            return(matching_id[0][0])
        else:
            return None

    def member_items(self, 
            query_string, 
            query_type, 
            provider_url_template="http://localhost:8080/github/members&%s"):
        enc = urllib.quote(query_string)

        #url = self.config.member_items["querytype"][query_type]['url'] % enc
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
            provider_url_template="http://localhost:8080/github/biblio&%s"):

        id = self.get_github_id(aliases)

        if not id:
            logger.info("Not checking biblio as no github id")
            return None

        #url = self.config.biblio['url'] % id
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
            provider_url_template="http://localhost:8080/github/aliases&%s"):

        id = self.get_github_id(aliases)

        #url = self.config.aliases['url'] % id
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
            provider_url_template="http://localhost:8080/github/metrics&%s"):

        id = self.get_github_id(aliases)

        #url = self.config.metrics['url'] % id
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

