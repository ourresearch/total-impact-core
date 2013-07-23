from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import simplejson, urllib, os, string, itertools

import logging
logger = logging.getLogger('ti.providers.mendeley')

class Mendeley(Provider):  

    example_id = ("doi", "10.1371/journal.pcbi.1000361")

    url = "http://www.mendeley.com"
    descr = " A research management tool for desktop and web."
    uuid_from_title_template = 'http://api.mendeley.com/oapi/documents/search/"%s"/?consumer_key=' + os.environ["MENDELEY_KEY"]
    metrics_from_uuid_template = "http://api.mendeley.com/oapi/documents/details/%s?consumer_key=" + os.environ["MENDELEY_KEY"]
    metrics_from_doi_template = "http://api.mendeley.com/oapi/documents/details/%s?type=doi&consumer_key=" + os.environ["MENDELEY_KEY"]
    metrics_from_pmid_template = "http://api.mendeley.com/oapi/documents/details/%s?type=pmid&consumer_key=" + os.environ["MENDELEY_KEY"]
    aliases_url_template = uuid_from_title_template

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

    def _get_page(self, url, cache_enabled=True):
        response = self.http_get(url, cache_enabled=cache_enabled)
        if response.status_code != 200:
            if response.status_code == 404:
                return None
            else:
                raise(self._get_error(response.status_code, response))
        return response.text
         
    def _get_uuid_lookup_page(self, title, cache_enabled=True):
        uuid_from_title_url = self.uuid_from_title_template % urllib.quote(title.encode("utf-8"))
        page = self._get_page(uuid_from_title_url, cache_enabled)
        if not page:
            raise ProviderContentMalformedError()            
        if not "documents" in page:
            raise ProviderContentMalformedError()
        return page

    def _get_metrics_lookup_page(self, template, id, cache_enabled=True):
        double_encoded_id = urllib.quote(urllib.quote(id, safe=""), safe="")
        metrics_url = template %double_encoded_id
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
                    logger.warning("Mendeley: NO TITLES for aliases, skipping")
                    continue  # nothing to see here.  Skip to next record

                if (len(str(biblio["year"])) != 4):
                    logger.warning("Mendeley: NO YEAR for aliases, skipping")
                    continue

                if (mendeley_title == aliases_title):
                    if (str(mendeley_record["year"]) == str(biblio["year"])):

                        # check if author name in common. if not, yell, but continue anyway
                        first_mendeley_surname = mendeley_record["authors"][0]["surname"]
                        has_matching_authors = first_mendeley_surname.lower() in biblio["authors"].lower()
                        if not has_matching_authors:
                            logger.warning("Mendeley: NO MATCHING AUTHORS between %s and %s" %(
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
                        logger.debug("Mendeley: years don't match %s and %s" %(
                            str(mendeley_record["year"]), str(biblio["year"])))
                else:
                    logger.debug("Mendeley: titles don't match %s and %s" %(
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
        # try lookup by title
        if not metrics_page:
            try:
                page = self._get_uuid_lookup_page(aliases_dict["biblio"][0]["title"], cache_enabled)
                if page:
                    uuid = self._get_uuid_from_title(aliases_dict, page)["uuid"]
                    if uuid:
                        logger.debug("Mendeley: uuid is %s for %s" %(uuid, aliases_dict["biblio"][0]["title"]))
                        metrics_page = self._get_metrics_lookup_page(self.metrics_from_uuid_template, uuid)
                    else:
                        logger.debug("Mendeley: couldn't find uuid for %s" %(aliases_dict["biblio"][0]["title"]))
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

        self.logger.debug("%s getting aliases for %s" % (self.provider_name, str(biblio)))

        if not provider_url_template:
            provider_url_template = self.aliases_url_template

        page = self._get_uuid_lookup_page(biblio["title"], cache_enabled)

        try:       
            new_aliases = self._extract_aliases(page, biblio)
        except (TypeError, AttributeError):
            self.logger.debug("Error.  returning with no new aliases")
            new_aliases = []

        return new_aliases

    def _extract_aliases(self, page, biblio):
        mendeley_ids = self._get_uuid_from_title({"doi":[None], "biblio":[biblio]}, page)
        if mendeley_ids:
            aliases_list = [(namespace, nid) for (namespace, nid) in mendeley_ids.iteritems()]
        else:
            aliases_list = []
        return aliases_list


