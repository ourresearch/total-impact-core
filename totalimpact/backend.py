import os, time, json, logging, threading, Queue

from totalimpact import dao, tiredis, default_settings
from totalimpact.models import ItemFactory
from totalimpact.providers.provider import ProviderFactory

logger = logging.getLogger('ti.backend')
logger.setLevel(logging.DEBUG)

class backendException(Exception):
    pass

class Backend(object):
    
    def __init__(self, couch_queues, myredis, dao):
        self.couch_queues = couch_queues
        self.myredis = myredis
        self.dao = dao
        self.name = "Backend"

    def push_on_update_queue(self, tiid, aliases):
        aliases_dict = ItemFactory.alias_dict_from_tuples(aliases)
        queue_string = json.dumps((tiid, aliases_dict))
        logger.info("{:20}: >>>PUSHING to redis {queue_string}".format(
            "update_queue", queue_string=queue_string))        
        self.myredis.lpush(["alias"], queue_string)

    def pop_from_update_queue(self):
        response = None
        popped = self.myredis.rpop(["alias"])
        if popped:
            logger.info("{:20}: <<<POPPED from redis, {popped}".format(
                "update_queue", popped=popped, len=len(popped)))        
            response = json.loads(popped) 
        return (response)

    def push_on_couch_queue(self, tiid, new_stuff, method_name):
        queue_contents = (tiid, new_stuff, method_name)
        logger.info("{:20}: >>>PUSHING to couch {queue_contents}".format(
            "couch_queue", queue_contents=queue_contents))        
        self.couch_queues[0].put((tiid, new_stuff, method_name))

    def pop_from_couch_queue(self):
        response = self.couch_queues[0].get()
        logger.info("{:20}: <<<POPPED from couch".format(
            "couch_queue"))
        self.couch_queues[0].task_done()
        return(response)

    def decide_who_to_call_next(self, item_aliases):
        simple_products_provider_lookup = {
            "dataset":["dryad"], 
            "software":["github"],
            "slides":["slideshare"], 
            "webpage":["webpage"], 
            "unknown":[]}

        # default to nothing
        aliases_providers = []
        biblio_providers = []
        metrics_providers = []

        has_alias_urls = "url" in item_aliases
        genre = ItemFactory.decide_genre(item_aliases)

        if (genre == "article"):
            if has_alias_urls:
                metrics_providers = "all"
                biblio_providers = ["pubmed", "crossref"]
            else:
                aliases_providers = ["pubmed", "crossref"]
        else:
            # relevant alias and biblio providers are always the same
            relevant_providers = simple_products_provider_lookup[genre]
            if has_alias_urls:
                # aliases are all done
                metrics_providers = "all"
                biblio_providers = relevant_providers
            else:
                aliases_providers = relevant_providers

        if metrics_providers == "all":
            metrics_providers = [provider.provider_name for provider in 
                ProviderFactory.get_providers(default_settings.PROVIDERS, "metrics")]
        return({
            "aliases_providers":aliases_providers,
            "biblio_providers":biblio_providers,
            "metrics_providers":metrics_providers})

    def add_aliases_to_update_queue(self, tiid, aliases_tuples, method="aliases"):
        self.push_on_couch_queue(tiid, aliases_tuples, method)
        self.push_on_update_queue(tiid, aliases_tuples)


    def wrapper(self, tiid, aliases, provider_names, method_name, callback):
        logger.info("{:20}: **Starting {tiid} {provider_names} {method_name} with {aliases}".format(
            "wrapper", tiid=tiid, method_name=method_name, aliases=aliases, provider_names=provider_names))

        alias_tuples = ItemFactory.alias_tuples_from_dict(aliases)

        response = None
        previous_responses = []
        # call the method for all the listed providers
        # 
        for provider_name in provider_names:
            provider = ProviderFactory.get_provider(provider_name)
            method = getattr(provider, method_name)

            try:
                new_response = method(alias_tuples)
                response = new_response
            except ProviderTimeout:
                logger.info("{:20}: **ProviderTimeout {tiid} {provider_name} {method_name} response: {new_response}".format(
                    "wrapper", tiid=tiid, provider_name=provider_name.upper(), method_name=method_name.upper(), new_response=new_response))

            logger.info("{:20}: **Ran {tiid} {provider_name} {method_name} response: {new_response}".format(
                "wrapper", tiid=tiid, provider_name=provider_name.upper(), method_name=method_name.upper(), new_response=new_response))

            if method_name == "metrics":
                self.myredis.decr_num_providers_left(tiid, provider_name)
            elif method_name == "aliases":
                # return all of the aliases, not just the new ones
                response += previous_responses
                response += alias_tuples
                # get unique tuples
                response = list(set(response))
            if new_response:
                previous_responses += new_response

        logger.info("{:20}: **Finished (now to callback) for {tiid} {provider_names} {method_name}".format(
            "wrapper", tiid=tiid, method_name=method_name, provider_names=provider_names))

        callback(tiid, response, method_name)
        return response


    def run(self):
        header = "run"
        #logger.info("{:20}: run".format(header))

        response = self.pop_from_update_queue()
        if response:
            (tiid, alias_dict) = response
            header = "run-{tiid}".format(tiid=tiid)

            relevant_provider_names = self.decide_who_to_call_next(alias_dict)
            logger.info("{:20}: decide_who_to_call_next returned {providers}".format(
                header, providers=relevant_provider_names))

            # alias providers are called in serial, so pass list of provider names to wrapper
            if relevant_provider_names["aliases_providers"]:
                t1 = threading.Thread(target=self.wrapper, 
                    args=(tiid,
                          alias_dict,
                          relevant_provider_names["aliases_providers"],
                          "aliases",
                          self.add_aliases_to_update_queue))
                t1.start()

            # biblio and metrics providers are called in parallel, so launch new thread for each
            for provider in relevant_provider_names["biblio_providers"]:
                t2 = threading.Thread(target=self.wrapper, 
                    args=(tiid, alias_dict, [provider], "biblio_providers", self.push_on_couch_queue))
                t2.start()
            for provider in relevant_provider_names["metrics_providers"]:
                t3 = threading.Thread(target=self.wrapper, 
                    args=(tiid, alias_dict, [provider], "metrics", self.push_on_couch_queue))
                t3.start()

            logger.info("{:20}: finished launching update threads".format(
                header))
        else:
            time.sleep(0.1)

    def run_in_loop(self):
        while True:
            self.run()


def run_couchworker(couch_queue, mydao):
    header = "couchworker"

    logger.info("{:20}: starting run_couchworker".format(
        header))

    while True:
        response = couch_queue.get()
        couch_queue.task_done()
        if response:
            logger.info("{:20}: <<<POPPED from couch queue".format(
                header))

            (tiid, payload, method_name) = response
            if not payload:
                logger.warning("{:20}: blank doc, nothing to save".format(
                    header))
            else:
                logger.info("{:20}: about to write about tiid:{tiid}".format(
                    header, tiid=tiid))
                item = mydao.get(tiid)
                if method_name=="aliases":
                    alias_dict = ItemFactory.alias_dict_from_tuples(payload)
                    merged_aliases = ItemFactory.merge_alias_dicts(alias_dict, item["aliases"])
                    item["aliases"] = merged_aliases
                    logger.info("{:20}: added aliases, saving item {item}".format(
                        header, item=item))
                    mydao.save(item)
                elif method_name=="biblio":
                    # just overwrite whatever was there
                    if not item["biblio"]:
                        item["biblio"] = payload
                        logger.info("{:20}: added biblio, saving item {item}".format(
                            header, item=item))
                        mydao.save(item)
                    else:
                        logger.info("{:20}: {tiid} already had biblio, not saving".format(
                            header, tiid=item["_id"]))
                elif method_name=="metrics":
                    for metric_name in payload:
                        snap = ItemFactory.build_snap(tiid, payload[metric_name], metric_name)
                        logger.info("{:20}: added metrics, saving snap {snap}".format(
                            header, snap=snap))
                        mydao.save(snap)
                else:
                    logger.info("{:20}: ack, supposed to save something i don't know about: " + str(payload))
        else:
            time.sleep(0.1)


def main():
    mydao = dao.Dao(os.environ["CLOUDANT_URL"], os.environ["CLOUDANT_DB"])
    mydao.update_design_doc()

    myredis = tiredis.from_url(os.getenv("REDISTOGO_URL"))

    couch_queue = Queue.Queue()
    couch_thread = threading.Thread(target=run_couchworker, 
                                    args=(couch_queue, mydao))
    couch_thread.start()

    backend = Backend([couch_queue], myredis, mydao)
    backend.run_in_loop()
 
if __name__ == "__main__":
    main()
