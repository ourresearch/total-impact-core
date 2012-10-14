from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError, ProviderItemNotFoundError
from xml.dom import minidom 
from xml.parsers.expat import ExpatError
import re

import logging
logger = logging.getLogger('ti.providers.orcid')

class Orcid(Provider):  
    descr = "Connecting research and researchers"
    url = "http://www.orcid.org"
    member_items_url_template = "http://pub.orcid.org/%s/orcid-works"
        
    DOI_PATTERN = re.compile("<work-external-identifier-id>(?P<downloads>10\..+)</work-external-identifier-id>")

    def __init__(self):
        super(Orcid, self).__init__()
        
    def _extract_members(self, page, query_string=None):
        if '<orcid-profile' not in page:
            raise ProviderContentMalformedError("Content does not contain expected text")

        dois = self.DOI_PATTERN.findall(page)
        if not dois:
            raise ProviderItemNotFoundError

        members = [("doi", doi) for doi in list(set(dois))]
        return(members)

    def member_items(self, 
            query_string, 
            provider_url_template=None, 
            cache_enabled=True):

        logger.debug("%20s getting member_items for %s" % (self.provider_name, query_string))

        if not provider_url_template:
            provider_url_template = self.member_items_url_template

        url = self._get_templated_url(provider_url_template, query_string, "members")

        # try to get a response from the data provider  
        response = self.http_get(url, cache_enabled=cache_enabled)

        if response.status_code != 200:
            self.logger.info("%s status_code=%i" 
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
