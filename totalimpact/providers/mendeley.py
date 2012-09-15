from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import simplejson, urllib, os, string

import logging
logger = logging.getLogger('ti.providers.mendeley')

class Mendeley(Provider):  

    example_id = ("doi", "10.1371/journal.pcbi.1000361")

    url = "http://www.mendeley.com"
    descr = " A research management tool for desktop and web."
    uuid_from_title_template = 'http://api.mendeley.com/oapi/documents/search/"%s"/?consumer_key=' + os.environ["MENDELEY_KEY"]
    metrics_from_uuid_template = "http://api.mendeley.com/oapi/documents/details/%s?consumer_key=" + os.environ["MENDELEY_KEY"]

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

    def _get_page(self, url):
        response = self.http_get(url)
        if response.status_code != 200:
            if response.status_code == 404:
                return None
            else:
                raise(self._get_error(response.status_code))
        return response.text
         
    def _get_uuid_lookup_page(self, title):
        uuid_from_title_url = self.uuid_from_title_template % title     
        page = self._get_page(uuid_from_title_url)
        if not "documents" in page:
            raise ProviderContentMalformedError()
        return page

    def _get_metrics_lookup_page(self, uuid):
        metrics_from_uuid_url = self.metrics_from_uuid_template %uuid
        page = self._get_page(metrics_from_uuid_url)
        if not "identifiers" in page:
            raise ProviderContentMalformedError()
        return page

    @classmethod
    def remove_punctuation(cls, str):
        # from http://stackoverflow.com/questions/265960/best-way-to-strip-punctuation-from-a-string-in-python
        return "".join(e for e in str if (e.isalnum() or e.isspace()))

    def _get_uuid_from_title(self, aliases_dict, page):
        doi = aliases_dict["doi"][0]
        data = provider._load_json(page)
        biblio = aliases_dict["biblio"][0]
        for mendeley_record in data["documents"]:
            if mendeley_record["doi"] == doi:
                uuid = mendeley_record["uuid"]
                # our job here is done
                return uuid
            else:
                if self.remove_punctuation(mendeley_record["title"]) == self.remove_punctuation(biblio["title"]):
                    if mendeley_record["year"] == biblio["year"]:
                        # check if author name in common. if not, yell, but continue anyway
                        first_mendeley_surname = mendeley_record["authors"][0]["surname"]
                        has_matching_authors = first_mendeley_surname in biblio["authors"]
                        if not has_matching_authors:
                            logger.warning("Mendeley: NO MATCHING AUTHORS between %s and %s" %(
                                first_mendeley_surname, biblio["authors"]))
                        # but return it anyway
                        uuid = mendeley_record["uuid"]
                        return uuid
                    else:
                        logger.debug("Mendeley: years don't match %s and %s" %(
                            str(mendeley_record["year"]), str(biblio["year"])))
                else:
                    logger.debug("Mendeley: titles don't match %s and %s" %(
                        self.remove_punctuation(mendeley_record["title"]), self.remove_punctuation(biblio["title"])))

        return None

    def _get_metrics_and_drilldown_from_uuid(self, page):
        metrics_dict = self._extract_metrics(page)
        metrics_and_drilldown = {}
        for metric_name in metrics_dict:
            drilldown_url = self._extract_provenance_url(page)
            metrics_and_drilldown[metric_name] = (metrics_dict[metric_name], drilldown_url)
        return metrics_and_drilldown  


    # default method; providers can override
    def metrics(self, 
            aliases,
            provider_url_template=None, # ignore this because multiple url steps
            cache_enabled=True):

        # Only lookup metrics for items with appropriate ids
        from totalimpact.models import ItemFactory
        aliases_dict = ItemFactory.alias_dict_from_tuples(aliases)

        if (not "biblio" in aliases_dict) or (not "doi" in aliases_dict):
            return {}

        page = self._get_uuid_lookup_page(aliases_dict["biblio"][0]["title"])
        if not page:
            return {}
        uuid = self._get_uuid_from_title(aliases_dict, page)
        if not uuid:
            logger.info("Mendeley: couldn't find uuid for %s" %(aliases_dict["biblio"][0]["title"]))
            return {}

        logger.info("Mendeley: uuid is %s for %s" %(uuid, aliases_dict["biblio"][0]["title"]))
        page = self._get_metrics_lookup_page(uuid)
        if not page:
            return {}
        metrics_and_drilldown = self._get_metrics_and_drilldown_from_uuid(page)

        return metrics_and_drilldown

