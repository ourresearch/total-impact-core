from werkzeug import generate_password_hash, check_password_hash
import datetime, hashlib, threading, json, time, copy, re

from totalimpact.providers.provider import ProviderFactory
from totalimpact.providers.provider import ProviderTimeout, ProviderServerError
from totalimpact import default_settings
from totalimpact.utils import Retry

# Master lock to ensure that only a single thread can write
# to the DB at one time to avoid document conflicts

import logging
logger = logging.getLogger('ti.models')

# setup to remove control characters from received IDs
# from http://stackoverflow.com/questions/92438/stripping-non-printable-characters-from-a-string-in-python
control_chars = ''.join(map(unichr, range(0,32) + range(127,160)))
control_char_re = re.compile('[%s]' % re.escape(control_chars))

class NotAuthenticatedError(Exception):
    pass

class MemberItems():

    def __init__(self, provider, redis):
        self.provider = provider
        self.redis = redis

    def start_update(self, str):
        paginate_dict = self.provider.paginate(str)
        hash = hashlib.md5(str.encode('utf-8')).hexdigest()
        t = threading.Thread(target=self._update, 
                            args=(paginate_dict["pages"], paginate_dict["number_entries"], hash), 
                            name=hash[0:4]+"_memberitems_thread")
        t.daemon = True
        t.start()
        return hash


    def get_sync(self, query):
        ret = {}
        start = time.time()
        ret = {
            "memberitems": self.provider.member_items(query),
            "pages": 1,
            "complete": 1,
            "error": False
        }
        ret["number_entries"] = len(ret["memberitems"])

        logger.debug(u"got {number_finished_memberitems} synchronous memberitems for query '{query}' in {elapsed} seconds.".format(
            number_finished_memberitems=len(ret["memberitems"]),
            query=query,
            elapsed=round(time.time() - start, 2)
        ))
        return ret

    def get_async(self, query_hash):
        query_status = self.redis.get_memberitems_status(query_hash)
        start = time.time()

        if not query_status:
            query_status = {"memberitems": [], "pages": 1, "complete": 0, "error": False} # don't know number_entries yet

        logger.debug(u"have finished {number_finished_memberitems} of asynchronous memberitems for query hash '{query_hash}' in {elapsed} seconds.".format(
                number_finished_memberitems=len(query_status["memberitems"]),
                query_hash=query_hash,
                elapsed=round(time.time() - start, 2)
            ))

        return query_status


    @Retry(3, ProviderTimeout, 0.1)
    def _update(self, pages, number_entries, query_key):

        status = {
            "memberitems": [],
            "pages": len(pages),
            "complete": 0,
            "number_entries": number_entries,
            "error": False            
        }
        self.redis.set_memberitems_status(query_key, status)
        for page in pages:
            try:
                memberitems = self.provider.member_items(page)
                status["memberitems"].append(memberitems)
            except (ProviderTimeout, ProviderServerError):
                status["error"] = True
            status["complete"] += 1
            self.redis.set_memberitems_status(query_key, status)

        return True




