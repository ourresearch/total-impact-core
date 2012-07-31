from werkzeug import generate_password_hash, check_password_hash
from totalimpact.providers.provider import ProviderFactory
from totalimpact import default_settings
import shortuuid, string, random, datetime

# Master lock to ensure that only a single thread can write
# to the DB at one time to avoid document conflicts

import logging
logger = logging.getLogger('ti.models')


class ItemFactory():

    all_static_meta = ProviderFactory.get_all_static_meta()


    @classmethod
    def get_item(cls, dao, tiid):
        res = dao.view("queues/by_tiid_with_snaps")
        rows = res[[tiid,0]:[tiid,1]].rows

        if not rows:
            return None
        else:
            item = rows[0]["value"]
            snaps = [row["value"] for row in rows[1:]]
            try:
                item = cls.build_item_for_client(item, snaps)
            except Exception, e:
                item = None
                logger.error("Exception %s: Unable to build item %s, %s, %s" % (e.__repr__(), tiid, str(item), str(snaps)))
        return item

    @classmethod
    def build_item_for_client(cls, item, snaps):
        item["biblio"]['genre'] = cls.decide_genre(item['aliases'])

            
        item["metrics"] = {} #not using what is in stored item for this
        for snap in snaps:
            metric_name = snap["metric_name"]
            item["metrics"][metric_name] = {}
            item["metrics"][metric_name]["values"] = {}
            item["metrics"][metric_name]["values"][snap["created"]] = snap["value"]
            item["metrics"][metric_name]["provenance_url"] = snap["drilldown_url"]
            item["metrics"][metric_name]["static_meta"] = cls.all_static_meta[metric_name]            
        return item
    


    @classmethod
    def build_snap(cls, tiid, metric_value_drilldown, metric_name):

        now = datetime.datetime.now().isoformat()
        shortuuid.set_alphabet('abcdefghijklmnopqrstuvwxyz1234567890')

        snap = {}
        snap["_id"] = shortuuid.uuid()[0:24]
        snap["type"] = "metric_snap"
        snap["metric_name"] = metric_name
        snap["tiid"] = tiid
        snap["created"] = now
        (value, drilldown_url) = metric_value_drilldown
        snap["value"] = value
        snap["drilldown_url"] = drilldown_url
        return snap        

    @classmethod
    def make(cls):

        now = datetime.datetime.now().isoformat()
        shortuuid.set_alphabet('abcdefghijklmnopqrstuvwxyz1234567890')

        item = {}
        item["_id"] = shortuuid.uuid()[0:24]
        item["aliases"] = {}
        item["biblio"] = {}
        item["last_modified"] = now
        item["created"] = now
        item["type"] = "item"
        item["providersWithMetricsCount"] = ProviderFactory.num_providers_with_metrics(default_settings.PROVIDERS)

        return item


    @classmethod
    def decide_genre(self, alias_dict):
        '''Uses available aliases to decide the item's genre'''

        if "doi" in alias_dict:
            if "10.5061/dryad." in "".join(alias_dict["doi"]):
                return "dataset"
            else:
                return "article"
        elif "pmid" in alias_dict:
            return "article"
        elif "url" in alias_dict:
            joined_urls = "".join(alias_dict["url"])
            if "slideshare.net" in joined_urls:
                return "slides"
            elif "github.com" in joined_urls:
                return "software"
            else:
                return "webpage"
        else:
            return "unknown"

    @classmethod
    def get_metric_names(self, providers_config):
        full_metric_names = []
        providers = ProviderFactory.get_providers(providers_config)
        for provider in providers:
            metric_names = provider.metric_names()
            for metric_name in metric_names:
                full_metric_names.append(provider.provider_name + ':' + metric_name)
        return full_metric_names




class CollectionFactory():

    @classmethod
    def make_id(cls, len=6):
        '''Make an id string.

        Currently uses only lowercase and digits for better say-ability. Six
        places gives us around 2B possible values.
        '''
        choices = string.ascii_lowercase + string.digits
        return ''.join(random.choice(choices) for x in range(len))

    @classmethod
    def make(cls):

        now = datetime.datetime.now().isoformat()
        collection = {}

        collection["_id"] = cls.make_id()
        collection["created"] = now
        collection["last_modified"] = now
        collection["type"] = "collection"

        return collection




# could make these saveable into the DB if we wanted, in the future
class Error():
    pass

