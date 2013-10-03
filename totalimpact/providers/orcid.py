import re
from totalimpact.providers import bibtex
from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError, ProviderItemNotFoundError

import logging
logger = logging.getLogger('ti.providers.orcid')

class Orcid(Provider):  
    descr = "Connecting research and researchers"
    url = "http://www.orcid.org"
    member_items_url_template = "http://pub.orcid.org/%s/orcid-works"
        
    def __init__(self):
        super(Orcid, self).__init__()
        
    def _parse_orcid_work(self, work):
        if not work:
            return {}

        biblio = {}
        try:
            biblio["year"] = work["publication-date"]["year"]["value"]
            biblio["year"] = re.sub("\D", "", biblio["year"])           
        except (KeyError, TypeError):
            biblio["year"]  = ""

        try:
            biblio["title"] = work["work-title"]["title"]["value"]
        except (KeyError, TypeError):
            biblio["title"]  = ""

        try:
            biblio["journal"] = work["work-title"]["subtitle"]["value"]
        except (KeyError, TypeError):
            biblio["journal"]  = ""

        try:
            biblio["url"] = work["url"]["value"]
        except (KeyError, TypeError):
            biblio["url"]  = ""

        biblio["authors"]  = ""

        return biblio

    def _extract_members(self, page, query_string=None):
        if 'orcid-profile' not in page:
            raise ProviderContentMalformedError("Content does not contain expected text")

        data = provider._load_json(page)
        members = []
        try:
            orcid_works = data["orcid-profile"]["orcid-activities"]["orcid-works"]["orcid-work"]
        except KeyError:
            return []

        for work in orcid_works:
            new_member = None
            try:
                ids = work["work-external-identifiers"]["work-external-identifier"]

                for myid in ids:
                    if myid['work-external-identifier-type'] == "DOI":
                        new_member = ("doi", myid['work-external-identifier-id']['value'])
                    if myid['work-external-identifier-type'] == "PMID":
                        new_member = ("pmid", myid['work-external-identifier-id']['value'])

            except KeyError:
                logger.info(u"no external identifiers, try saving whole citation")
                biblio = self._parse_orcid_work(work)
                new_member = ("biblio", biblio)

            if new_member:
                members += [new_member]    

        if not members:
            raise ProviderItemNotFoundError

        return(members)

    def member_items(self, 
            query_string, 
            provider_url_template=None, 
            cache_enabled=True):

        logger.debug(u"%20s getting member_items for %s" % (self.provider_name, query_string))

        if not provider_url_template:
            provider_url_template = self.member_items_url_template

        query_string = query_string.replace("http://orcid.org/", "")
        url = self._get_templated_url(provider_url_template, query_string, "members")
        headers = {}
        headers["accept"] = "application/json"

        # try to get a response from the data provider  
        # cache FALSE for now because people probably changing ORCIDs a lot
        response = self.http_get(url, headers=headers, cache_enabled=False) 

        if response.status_code != 200:
            self.logger.info(u"%s status_code=%i" 
                % (self.provider_name, response.status_code))            
            if response.status_code == 404:
                raise ProviderItemNotFoundError
            elif response.status_code == 303: #redirect
                pass                
            else:
                self._get_error(response.status_code, response)

        # extract the member ids
        try:
            members = self._extract_members(response.text, query_string)
        except (AttributeError, TypeError):
            members = []

        return(members)
