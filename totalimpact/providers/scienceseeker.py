from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
import hashlib
import simplejson

import logging
logger = logging.getLogger('ti.providers.scienceseeker')

class Scienceseeker(Provider):  

    example_id = ("doi", "10.1016/j.cbpa.2010.06.169")
    metrics_url_template = "http://scienceseeker.org/search/default/?type=post&filter0=citation&modifier0=id-all&value0=%s"
    provenance_url_template = "http://scienceseeker.org/posts/?type=post&filter0=citation&modifier0=id-all&value0=%s"
    url = "http://www.scienceseeker.org"
    descr = "Science news from science newsmakers"
    static_meta_dict = {
        "blog_posts": {
            "display_name": "blog posts",
            "provider": "Science Seeker",
            "provider_url": "http://www.scienceseeker.org",
            "description": "The number of blog posts that cite this item.",
            "icon": "http://scienceseeker.org/images/misc/favicon.ico"
        }
    }

    def __init__(self):
        super(Scienceseeker, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        return("doi" == namespace)

    def _extract_metrics(self, page, status_code=200, id=None): 
        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))

        if ("subjectseeker" not in page) and ("Recent Posts" not in page):
            raise ProviderContentMalformedError

        (doc, lookup_function) = provider._get_doc_from_xml(page)  
        if not doc:
            return {}
        try:
            feed_doc = doc.getElementsByTagName("feed")
            entry_docs = feed_doc[0].getElementsByTagName("entry")
            number_blog_posts = len(entry_docs)
        except (KeyError, IndexError, TypeError):
            return {}

        if number_blog_posts:
            metrics_dict = {'scienceseeker:blog_posts': number_blog_posts}
        else:
            metrics_dict = {}
        return metrics_dict



