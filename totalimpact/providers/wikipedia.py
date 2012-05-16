from totalimpact.providers.provider import Provider, ProviderContentMalformedError
from xml.dom import minidom
from xml.parsers.expat import ExpatError

import logging
logger = logging.getLogger('providers.wikipedia')

class Wikipedia(Provider):  
    """ Gets numbers of citations for a DOI document from wikipedia using
        the Wikipedia search interface.
    """

    metric_names = ['wikipedia:mentions']
    metric_namespaces = ["doi"]
    alias_namespaces = None
    biblio_namespaces = None

    provides_members = False
    provides_aliases = False
    provides_metrics = True
    provides_biblio = False

    provenance_url_template = "http://en.wikipedia.org/wiki/Special:Search?search='%s'&go=Go"
    metrics_url_template = "http://en.wikipedia.org/w/api.php?action=query&list=search&srprop=timestamp&format=xml&srsearch='%s'"

    example_id = ("doi", "10.1371/journal.pcbi.1000361")

    def __init__(self):
        super(Wikipedia, self).__init__()

    def is_relevant_alias(self, alias):
        if not alias:
            return False
        (namespace, nid) = alias
        is_relevant = (namespace=="doi")
        return is_relevant

    def _extract_metrics(self, page, id=None):
        try:
            doc = minidom.parseString(page)
        except ExpatError, e:
            raise ProviderContentMalformedError("Content parse provider supplied XML document")

        searchinfo = doc.getElementsByTagName('searchinfo')
        if not searchinfo:
            raise ProviderContentMalformedError("No searchinfo in response document")
        val = searchinfo[0].attributes['totalhits'].value

        metrics_dict = {"wikipedia:mentions": int(val)}

        return metrics_dict
            

