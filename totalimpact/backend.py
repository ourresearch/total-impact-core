#!/usr/bin/env python

import os, time, json, logging, Queue, copy, sys, datetime
from collections import defaultdict

from totalimpact import tiredis, default_settings, db
from totalimpact import item as item_module
import tasks
from totalimpact.providers.provider import ProviderFactory, ProviderError

logger = logging.getLogger('ti.backend')
logger.setLevel(logging.DEBUG)

thread_count = defaultdict(dict)




class RedisQueue(object):
    def __init__(self, queue_name, myredis):
        self.queue_name = queue_name
        self.myredis = myredis
        self.name = queue_name + "_queue"

    def push(self, message):
        message_json = json.dumps(message)
        # logger.info(u"{:20}: /biblio_print >>>PUSHING to redis {message_json}".format(
        #     self.name, message_json=message_json)) 
        queue_length = self.myredis.llen(self.queue_name)       
        # logger.info(u">>>PUSHING to redis queue {queue_name}, current length {queue_length}".format(
        #     queue_name=self.name, queue_length=queue_length)) 
        self.myredis.lpush(self.queue_name, message_json)

    @classmethod
    def pop(cls, redis_queues, myredis):
        message = None
        logger.debug(u"about to pop from redis".format())

        (popped_queue_name, message_json) = myredis.brpop([queue.queue_name for queue in redis_queues]) 
        if message_json:
            queue_length = myredis.llen(popped_queue_name)                   
            logger.debug(u"{:20}: <<<POPPED from redis, current length {queue_length}, now to parse message".format(
                popped_queue_name, queue_length=queue_length))
            try:
                # logger.debug(u"{:20}: <<<POPPED from redis: starts {message_json}".format(
                #     self.name, message_json=message_json[0:50]))        
                message = json.loads(message_json) 
            except (TypeError, KeyError):
                logger.info(u"{:20}: ERROR processing redis message {message_json}".format(
                    popped_queue_name, message_json=message_json))
        return message



class Worker(object):
    def run_in_loop(self):
        while True:
            self.run()

    def spawn_and_loop(self):
        # t = threading.Thread(target=self.run_in_loop, name=self.name+"_thread")
        # t.daemon = True
        # t.start()    
        run_in_loop()



class Backend(Worker):
    def __init__(self, alias_queues, myredis):
        self.alias_queues = alias_queues
        self.myredis = myredis
        self.name = "Backend"

    @classmethod
    def sniffer(cls, item_aliases, aliases_providers_run, provider_config=default_settings.PROVIDERS):

        # default to nothing
        aliases_providers = []
        biblio_providers = []
        metrics_providers = []
        (genre, host) = item_module.decide_genre(item_aliases)

        all_metrics_providers = [provider.provider_name for provider in 
                        ProviderFactory.get_providers(provider_config, "metrics")]

        has_enough_alias_urls = ("url" in item_aliases)
        if has_enough_alias_urls:
            if ("doi" in item_aliases):
                has_enough_alias_urls = (len([url for url in item_aliases["url"] if url.startswith("http://dx.doi.org")]) > 0)

        if (genre == "article") and (host != "arxiv"):
            if not "mendeley" in aliases_providers_run:
                aliases_providers = ["mendeley"]
            elif not "crossref" in aliases_providers_run:
                aliases_providers = ["crossref"]  # do this before pubmed because might tease doi from url
            elif not "pubmed" in aliases_providers_run:
                aliases_providers = ["pubmed"]
            elif not "altmetric_com" in aliases_providers_run:
                aliases_providers = ["altmetric_com"]
            else:
                metrics_providers = all_metrics_providers
                biblio_providers = ["crossref", "pubmed", "mendeley", "webpage"]
        elif ("doi" in item_aliases) or (host == "arxiv"):
            if (set([host, "altmetric_com"]) == set(aliases_providers_run)):
                metrics_providers = all_metrics_providers
                biblio_providers = [host, "mendeley"]
            else:     
                if not "altmetric_com" in aliases_providers_run:
                    aliases_providers = ["altmetric_com"]
                else:
                    aliases_providers = [host]
        else:
            # relevant alias and biblio providers are always the same
            relevant_providers = [host]
            if relevant_providers == ["unknown"]:
                relevant_providers = ["webpage"]
            # if all the relevant providers have already run, then all the aliases are done
            # or if it already has urls
            if has_enough_alias_urls or (set(relevant_providers) == set(aliases_providers_run)):
                metrics_providers = all_metrics_providers
                biblio_providers = relevant_providers
            else:
                aliases_providers = relevant_providers

        return({
            "aliases":aliases_providers,
            "biblio":biblio_providers,
            "metrics":metrics_providers})


    def providers_too_busy(self, max_requests=50):
        global thread_count

        for provider_name in thread_count:
            if provider_name != "webpage":
                num_active_threads_for_this_provider = len(thread_count[provider_name])
                if num_active_threads_for_this_provider >= max_requests:
                    return provider_name
        return None

    def run(self):
        global thread_count

        # go through alias_queues, with highest priority first
        alias_message = RedisQueue.pop([self.alias_queues["high"], self.alias_queues["low"]], self.myredis)

        if alias_message:
            tiid = alias_message["tiid"]
            aliases_dict = alias_message["aliases_dict"]
            analytics_credentials = alias_message["analytics_credentials"]
            alias_providers_already_run = alias_message["alias_providers_already_run"]            

            relevant_provider_names = self.sniffer(aliases_dict, alias_providers_already_run)
            #logger.info(u"/biblio_print, backend for {tiid} sniffer got input {alias_dict}".format(
            #    tiid=tiid, alias_dict=alias_dict))
            logger.info(u"backend for {tiid} sniffer returned {providers}".format(
                tiid=tiid, providers=relevant_provider_names))

            # list out the method names so they are run in that priority, biblio before metrics
            for method_name in ["aliases", "biblio", "metrics"]:
                for provider_name in relevant_provider_names[method_name]:

                    provider_message = {
                        "tiid": tiid, 
                        "aliases_dict": aliases_dict, 
                        "method_name": method_name, 
                        "analytics_credentials": analytics_credentials,
                        "alias_providers_already_run": alias_providers_already_run}
                    try:
                        print "ADDING TO CELERY"
                        tasks.provider_run.delay(provider_message, provider_name)
                    except KeyError:
                        #removed a provider?
                        logger.warning(u"KeyError in backend for {tiid} on {provider_name}".format(
                            tiid=tiid, provider_name=provider_name))
        else:
            #time.sleep(0.1)  # is this necessary?
            pass



def main():

    mydao = None

    myredis = tiredis.from_url(os.getenv("REDISTOGO_URL"))

    alias_queues = {
        "high": RedisQueue("aliasqueue_high", myredis), 
        "low": RedisQueue("aliasqueue_low", myredis)
        }
    # to clear alias_queue:
    #import redis, os
    #myredis = redis.from_url(os.getenv("REDISTOGO_URL"))
    #myredis.delete("aliasqueue_high")


    backend = Backend(alias_queues, myredis)
    try:
        backend.run_in_loop() # don't need to spawn this one
    except (KeyboardInterrupt, SystemExit): 
        # this approach is per http://stackoverflow.com/questions/2564137/python-how-to-terminate-a-thread-when-main-program-ends
        sys.exit()
 
if __name__ == "__main__":
    main()
