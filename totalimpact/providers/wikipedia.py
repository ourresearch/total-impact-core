from totalimpact.providers import provider
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

    def _extract_metrics(self, page, status_code=200, id=None):
        logger.info("_extract_metrics with %s, %i,\n%s\n" % (id, status_code, page))

        if status_code != 200:
            if (status_code == 404):
                return {}
            else:
                raise(self._get_error(status_code))

        try:
            doc = minidom.parseString(page)
        except ExpatError, e:
            raise ProviderContentMalformedError("Content parse provider supplied XML document")

        searchinfo = doc.getElementsByTagName('searchinfo')
        if not searchinfo:
            raise ProviderContentMalformedError("No searchinfo in response document")
        val = searchinfo[0].attributes['totalhits'].value

        metrics_dict = {"wikipedia:mentions": int(val)}
        logger.info("_extract_metrics returns metrics_dict %s" % (str(metrics_dict)))

        return metrics_dict
            

