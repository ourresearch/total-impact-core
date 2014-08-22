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

import logging
logger = logging.getLogger('ti.providers.mendeley')
shared_redis = tiredis.from_url(os.getenv("REDIS_URL"), db=0)


### NOTE:  TO GET MENDELEY PROVIDER WORKING
# you need to bootstrap the access and refresh tokens into REDIS_URL from production redis.
# instructions on how to do that are in repo total-impact-deploy/instructions.md


# from https://gist.github.com/jalperin/8b3367b65012291fe23f
def get_token():
    client_auth = requests.auth.HTTPBasicAuth(os.getenv("MENDELEY_OAUTH2_CLIENT_ID"), os.getenv("MENDELEY_OAUTH2_SECRET"))
    post_data = {"grant_type": "authorization_code",
                 "code": os.getenv("MENDELEY_OAUTH2_GENERAGED_CODE"),
                 "redirect_uri": "http://impactstory.org"}
    token_url = 'https://api-oauth2.mendeley.com/oauth/token'
    response = requests.post(token_url,
                             auth=client_auth,
                             data=post_data)
    token_json = response.json()
    return token_json

def renew_token(access_token, refresh_token):
    logger.debug(u"Mendeley: renewing access token")
    client_auth = requests.auth.HTTPBasicAuth(os.getenv("MENDELEY_OAUTH2_CLIENT_ID"), os.getenv("MENDELEY_OAUTH2_SECRET"))
    headers = {"Authorization": "bearer " + access_token}
    post_data = {"grant_type": "refresh_token",
                 "refresh_token": refresh_token}
    token_url = 'https://api-oauth2.mendeley.com/oauth/token'
    response = requests.post(token_url,
                             auth=client_auth,
                             data=post_data)
    token_json = response.json()
    return token_json

def store_access_cred(token_response):
    access_token = token_response["access_token"]
    shared_redis.set("MENDELEY_OAUTH2_ACCESS_TOKEN", access_token)
    refresh_token = token_response["refresh_token"]
    shared_redis.set("MENDELEY_OAUTH2_REFRESH_TOKEN", refresh_token)
    return (access_token, refresh_token)

def get_access_token(force_renew=False):
    access_token = shared_redis.get("MENDELEY_OAUTH2_ACCESS_TOKEN")
    if force_renew:
        previous_refresh_token = shared_redis.get("MENDELEY_OAUTH2_REFRESH_TOKEN")
        token_response = renew_token(access_token, previous_refresh_token)
        (access_token, refresh_token) = store_access_cred(token_response)
    elif not access_token:
        token_response = get_token()
        (access_token, refresh_token) = store_access_cred(token_response)
    return access_token


# from http://stackoverflow.com/questions/4293460/how-to-add-custom-parameters-to-an-url-query-string-with-python
def set_query_parameter(url, param_name, param_value):
    """Given a URL, set or replace a query parameter and return the
    modified URL.

    >>> set_query_parameter('http://example.com?foo=bar&biz=baz', 'foo', 'stuff')
    'http://example.com?foo=stuff&biz=baz'

    """
    scheme, netloc, path, query_string, fragment = urlsplit(url)
    query_params = parse_qs(query_string)

    query_params[param_name] = [param_value]
    new_query_string = urlencode(query_params, doseq=True)

    return urlunsplit((scheme, netloc, path, new_query_string, fragment))



class Mendeley(Provider):  

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
        "readers": {
            "display_name": "readers",
            "provider": "Mendeley",
            "provider_url": "http://www.mendeley.com/",
            "description": "The number of readers who have added the article to their libraries",
            "icon": "http://www.mendeley.com/favicon.ico",
        },    
        "groups": {
            "display_name": "groups",
            "provider": "Mendeley",
            "provider_url": "http://www.mendeley.com/",
            "description": "The number of groups who have added the article to their libraries",
            "icon": "http://www.mendeley.com/favicon.ico",
        },
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
        super(Mendeley, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        # right now restricted to doi because we check the title lookup matches doi
        ## to keep precision high.  Later could experiment with opening this up.
        relevant = (namespace=="doi")
        return(relevant)

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


    def _extract_provenance_url(self, page, status_code=200, id=None):
        data = provider._load_json(page)
        try:
            provenance_url = data['mendeley_url']
        except KeyError:
            provenance_url = ""
        return provenance_url        

    @Retry(2, ProviderAuthenticationError, 0.1)
    def _get_page(self, url, cache_enabled=True):
        url_with_access_token = set_query_parameter(url, "access_token", get_access_token())
        response = self.http_get(url_with_access_token, cache_enabled=cache_enabled)
        if response.status_code != 200:
            if response.status_code == 404:
                return None
            elif response.status_code == 401:
                logger.debug(u"got status 401 so going to try renewing access token")
                get_access_token(force_renew=True)
                raise ProviderAuthenticationError("not authenticated")
            else:
                raise(self._get_error(response.status_code, response))
        return response.text
         
    def _get_uuid_lookup_page(self, title, cache_enabled=True):
        uuid_from_title_url = self.uuid_from_title_template % (urllib.quote(title.encode("utf-8")))
        page = self._get_page(uuid_from_title_url, cache_enabled)
        if not page:
            raise ProviderContentMalformedError()            
        if not "documents" in page:
            raise ProviderContentMalformedError()
        return page

    def _get_metrics_lookup_page(self, template, id, cache_enabled=True):
        double_encoded_id = urllib.quote(urllib.quote(id, safe=""), safe="")
        metrics_url = template %(double_encoded_id)
        page = self._get_page(metrics_url, cache_enabled)
        if page:
            if not "identifiers" in page:
                page = None
        return page

    @classmethod
    def remove_punctuation(cls, input):
        # from http://stackoverflow.com/questions/265960/best-way-to-strip-punctuation-from-a-string-in-python
        no_punc = input
        if input:
            no_punc = "".join(e for e in input if (e.isalnum() or e.isspace()))
        return no_punc

    def _get_uuid_from_title(self, aliases_dict, page):
        data = provider._load_json(page)
        try:
            doi = aliases_dict["doi"][0]
        except KeyError:
            doi = None

        try:
            biblio = aliases_dict["biblio"][0]
        except KeyError:
            biblio = None

        for mendeley_record in data["documents"]:
            if doi and (mendeley_record["doi"] == doi):
                uuid = mendeley_record["uuid"]
                return {"uuid": uuid}
            else:
                # more complicated.  Try to match title and year.
                try:
                    mendeley_title = self.remove_punctuation(mendeley_record["title"]).lower()
                    aliases_title = self.remove_punctuation(biblio["title"]).lower()
                except (TypeError, KeyError, AttributeError):
                    logger.warning(u"Mendeley: NO TITLES for aliases, skipping")
                    continue  # nothing to see here.  Skip to next record

                try:
                    if (len(str(biblio["year"])) != 4):
                        logger.warning(u"Mendeley: NO YEAR for aliases, skipping")
                        continue
                except (TypeError, KeyError, AttributeError):
                    logger.warning(u"Mendeley: NO YEAR for aliases, skipping")
                    continue  # nothing to see here.  Skip to next record

                if (mendeley_title == aliases_title):
                    if (str(mendeley_record["year"]) == str(biblio["year"])):

                        # check if author name in common. if not, yell, but continue anyway
                        first_mendeley_surname = mendeley_record["authors"][0]["surname"]
                        has_matching_authors = first_mendeley_surname.lower() in biblio["authors"].lower()
                        if not has_matching_authors:
                            logger.warning(u"Mendeley: NO MATCHING AUTHORS between %s and %s" %(
                                first_mendeley_surname, biblio["authors"]))
                        # but return it anyway
                        response = {}
                        for id_type in ["uuid", "mendeley_url", "doi", "pmid"]:
                            try:
                                if mendeley_record[id_type]:
                                    if id_type == "mendeley_url":
                                        response["url"] = mendeley_record[id_type]
                                    else:
                                        response[id_type] = mendeley_record[id_type]
                            except KeyError:
                                pass
                        return response
                    else:
                        logger.debug(u"Mendeley: years don't match %s and %s" %(
                            str(mendeley_record["year"]), str(biblio["year"])))
                else:
                    logger.debug(u"Mendeley: titles don't match /biblio_print %s and %s" %(
                        self.remove_punctuation(mendeley_record["title"]), self.remove_punctuation(biblio["title"])))
        # no joy
        return None

    def _get_metrics_and_drilldown_from_metrics_page(self, page):
        metrics_dict = self._extract_metrics(page)
        metrics_and_drilldown = {}
        for metric_name in metrics_dict:
            drilldown_url = self._extract_provenance_url(page)
            metrics_and_drilldown[metric_name] = (metrics_dict[metric_name], drilldown_url)
        return metrics_and_drilldown  


    def metrics(self, 
            aliases,
            provider_url_template=None, # ignore this because multiple url steps
            cache_enabled=True):

        # Only lookup metrics for items with appropriate ids
        from totalimpact import item
        aliases_dict = item.alias_dict_from_tuples(aliases)

        metrics_page = None    
        # try lookup by doi
        try:
            metrics_page = self._get_metrics_lookup_page(self.metrics_from_doi_template, aliases_dict["doi"][0], cache_enabled)
        except KeyError:
            pass
        # try lookup by pmid
        if not metrics_page:
            try:
                metrics_page = self._get_metrics_lookup_page(self.metrics_from_pmid_template, aliases_dict["pmid"][0], cache_enabled)
            except KeyError:
                pass
        # try lookup by arxiv
        if not metrics_page:
            try:
                metrics_page = self._get_metrics_lookup_page(self.metrics_from_arxiv_template, aliases_dict["arxiv"][0], cache_enabled)
            except KeyError:
                pass
        # try lookup by title
        if not metrics_page:
            try:
                page = self._get_uuid_lookup_page(aliases_dict["biblio"][0]["title"], cache_enabled)
                if page:
                    uuid = self._get_uuid_from_title(aliases_dict, page)["uuid"]
                    if uuid:
                        logger.debug(u"Mendeley: uuid is %s for %s" %(uuid, aliases_dict["biblio"][0]["title"]))
                        metrics_page = self._get_metrics_lookup_page(self.metrics_from_uuid_template, uuid)
                    else:
                        logger.debug(u"Mendeley: couldn't find uuid for %s" %(aliases_dict["biblio"][0]["title"]))
            except (KeyError, TypeError):
                pass
        # give up!
        if not metrics_page:
            return {}

        metrics_and_drilldown = self._get_metrics_and_drilldown_from_metrics_page(metrics_page)

        return metrics_and_drilldown

    def aliases(self, 
            aliases, 
            provider_url_template=None,
            cache_enabled=True):            

        aliases_dict = provider.alias_dict_from_tuples(aliases)

        if not "biblio" in aliases_dict:
            return []
        if ("doi" in aliases_dict) or ("pmid" in aliases_dict):
            # have better sources, leave them to it.
            return []

        new_aliases = []
        for alias in aliases_dict["biblio"]:
            new_aliases += self._get_aliases_for_id(alias, provider_url_template, cache_enabled)
        
        # get uniques for things that are unhashable
        new_aliases_unique = [k for k,v in itertools.groupby(sorted(new_aliases))]

        return new_aliases_unique

    def _get_aliases_for_id(self, 
            biblio, 
            provider_url_template=None, 
            cache_enabled=True):

        self.logger.debug(u"%s getting aliases for %s" % (self.provider_name, str(biblio)))

        if not provider_url_template:
            provider_url_template = self.aliases_url_template

        page = self._get_uuid_lookup_page(biblio["title"], cache_enabled)

        try:       
            new_aliases = self._extract_aliases(page, biblio)
        except (TypeError, AttributeError):
            self.logger.debug(u"Error.  returning with no new aliases")
            new_aliases = []

        return new_aliases

    def _extract_aliases(self, page, biblio):
        mendeley_ids = self._get_uuid_from_title({"doi":[None], "biblio":[biblio]}, page)
        if mendeley_ids:
            aliases_list = [(namespace, nid) for (namespace, nid) in mendeley_ids.iteritems()]
        else:
            aliases_list = []
        return aliases_list


    def get_biblio_for_id(self, 
            id,
            provider_url_template=None, 
            cache_enabled=True):

        self.logger.debug(u"%s getting biblio for %s" % (self.provider_name, id))

        if not provider_url_template:
            provider_url_template = self.biblio_url_template
        page = self._get_metrics_lookup_page(provider_url_template, id, cache_enabled)
        
        # extract the aliases
        try:
            biblio_dict = self._extract_biblio(page, id)
        except (AttributeError, TypeError):
            biblio_dict = {}

        if biblio_dict and ("is_oa_journal" in biblio_dict) and (biblio_dict["is_oa_journal"]=='True'):
            biblio_dict["free_fulltext_url"] = self.doi_url_template %id
        elif biblio_dict and ("issn" in biblio_dict) and provider.is_issn_in_doaj(biblio_dict["issn"]):
            biblio_dict["free_fulltext_url"] = self.doi_url_template %id

        return biblio_dict


    def _extract_biblio(self, page, id=None):
        biblio_dict = {}

        dict_of_keylists = {
            'issn' : ['identifiers', 'issn'],
            'oai_id' : ['identifiers', 'oai_id'],
            'abstract' : ['abstract'],
            'keywords' : ['keywords']
        }
        biblio_dict = provider._extract_from_json(page, dict_of_keylists, include_falses=False)
        if "issn" in biblio_dict:
            biblio_dict["issn"] = biblio_dict["issn"].replace("-", "")
        if "keywords" in biblio_dict:
            biblio_dict["keywords"] = "; ".join(biblio_dict["keywords"])


        dict_of_keylists = {
            'is_oa_journal' : ['oa_journal']
        }
        biblio_dict.update(provider._extract_from_json(page, dict_of_keylists, include_falses=True))
        if biblio_dict and "is_oa_journal" in biblio_dict:
            biblio_dict["is_oa_journal"] = str(biblio_dict["is_oa_journal"]) # cast boolean to string
        return biblio_dict 

