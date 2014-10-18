from __future__ import absolute_import

from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError, ProviderAuthenticationError
from totalimpact import tiredis
from totalimpact.utils import Retry

import simplejson, urllib, os, string, itertools
import requests
import requests.auth
import redis
from urllib import urlencode
from urlparse import parse_qs, urlsplit, urlunsplit

# need to get system mendeley library
import mendeley as mendeley_lib

import logging
logger = logging.getLogger('ti.providers.mendeley_new')


class Mendeley_New(Provider):  

    example_id = ("doi", "10.1371/journal.pcbi.1000361")

    url = "http://www.mendeley.com"
    descr = " A research management tool for desktop and web."
    uuid_from_title_template = 'https://api-oauth2.mendeley.com/oapi/documents/search/"%s"/'
    metrics_from_uuid_template = "https://api-oauth2.mendeley.com/oapi/documents/details/%s"
    metrics_from_doi_template = "https://api-oauth2.mendeley.com/oapi/documents/details/%s?type=doi"
    metrics_from_pmid_template = "https://api-oauth2.mendeley.com/oapi/documents/details/%s?type=pmid"
    metrics_from_arxiv_template = "https://api-oauth2.mendeley.com/oapi/documents/details/%s?type=arxiv"
    aliases_url_template = uuid_from_title_template
    biblio_url_template = metrics_from_doi_template
    doi_url_template = "http://dx.doi.org/%s"

    static_meta_dict = {
        "discipline": {
            "display_name": "discipline, top 3 percentages",
            "provider": "Mendeley",
            "provider_url": "http://www.mendeley.com/",
            "description": "Percent of readers by discipline, for top three disciplines (csv, api only)",
            "icon": "http://www.mendeley.com/favicon.ico",
        },   
        "career_stage": {
            "display_name": "career stage, top 3 percentages",
            "provider": "Mendeley",
            "provider_url": "http://www.mendeley.com/",
            "description": "Percent of readers by career stage, for top three career stages (csv, api only)",
            "icon": "http://www.mendeley.com/favicon.ico",
        },   
        "country": {
            "display_name": "country, top 3 percentages",
            "provider": "Mendeley",
            "provider_url": "http://www.mendeley.com/",
            "description": "Percent of readers by country, for top three countries (csv, api only)",
            "icon": "http://www.mendeley.com/favicon.ico",
        }
    }

    def __init__(self):
        super(Mendeley_New, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        # right now restricted to doi because we check the title lookup matches doi
        ## to keep precision high.  Later could experiment with opening this up.
        relevant = (namespace=="doi")
        return(relevant)


    def _extract_provenance_url(self, page, status_code=200, id=None):
        data = provider._load_json(page)
        try:
            provenance_url = data['mendeley_url']
        except KeyError:
            provenance_url = ""
        return provenance_url        

    def _get_metrics_and_drilldown_from_api(self, doc):
        metrics_dict = self._extract_metrics(page)
        metrics_and_drilldown = {}
        for metric_name in metrics_dict:
            drilldown_url = self._extract_provenance_url(page)
            metrics_and_drilldown[metric_name] = (metrics_dict[metric_name], drilldown_url)
        return metrics_and_drilldown  

    def _extract_metrics(self, page, status_code=200, id=None):
        if not "identifiers" in page:
            raise ProviderContentMalformedError()

        dict_of_keylists = {"mendeley:readers": ["stats", "readers"], 
                            "mendeley:discipline": ["stats", "discipline"],
                            "mendeley:career_stage": ["stats", "status"],
                            "mendeley:country": ["stats", "country"],
                            "mendeley:groups" : ["groups"]}

        metrics_dict = provider._extract_from_json(page, dict_of_keylists)

        # get count of groups
        try:
            metrics_dict["mendeley:groups"] = len(metrics_dict["mendeley:groups"])
        except (TypeError, KeyError):
            # don't add null or zero metrics
            pass

        return metrics_dict


    def metrics(self, 
            aliases,
            provider_url_template=None, # ignore this because multiple url steps
            cache_enabled=True):

        # Only lookup metrics for items with appropriate ids
        from totalimpact import item
        aliases_dict = item.alias_dict_from_tuples(aliases)


        mendeley = mendeley_lib.Mendeley(
            client_id=os.getenv("MENDELEY_OAUTH2_CLIENT_ID"), 
            client_secret=os.getenv("MENDELEY_OAUTH2_SECRET"))
        session = mendeley.start_client_credentials_flow().authenticate()

        metrics_and_drilldown = {}
        lookup_by = None
        # try lookup by doi
        if "doi" in aliases_dict:
            lookup_by = "doi"
        elif "pmid" in aliases_dict:
            lookup_by = "pmid"
        elif "arxiv" in aliases_dict:
            lookup_by = "arxiv"

        if not lookup_by:
            return metrics_and_drilldown

        try:
            kwargs = {lookup_by:aliases_dict[lookup_by][0], "view":'stats'}
            doc = session.catalog.by_identifier(**kwargs)
            drilldown_url = doc.link
            metrics_and_drilldown["mendeley_new:readers"] = (doc.reader_count, drilldown_url)
            metrics_and_drilldown["mendeley_new:countries"] = (doc.reader_count_by_country, drilldown_url)
        except KeyError:
            pass
            
        return metrics_and_drilldown



