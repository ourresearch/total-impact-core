#!/usr/bin/env python

import os, time, json, logging, threading, Queue, copy, sys, datetime
from collections import defaultdict

from totalimpact import tiredis, default_settings, db
from totalimpact import item as item_module
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
        self.myredis.lpush(self.queue_name, message_json)

    def pop(self):
        #blocking pop
        message = None
        received = self.myredis.brpop([self.queue_name], timeout=5) #maybe timeout not necessary
        if received:
            queue, message_json = received
            try:
                # logger.debug(u"{:20}: <<<POPPED from redis: starts {message_json}".format(
                #     self.name, message_json=message_json[0:50]))        
                message = json.loads(message_json) 
            except (TypeError, KeyError):
                logger.info(u"{:20}: ERROR processing redis message {message_json}".format(
                    self.name, message_json=message_json))
        return message


class PythonQueue(object):
    def __init__(self, queue_name):
        self.queue_name = queue_name
        self.queue = Queue.Queue()

    def push(self, message):
        self.queue.put(copy.deepcopy(message))
        #logger.info(u"{:20}: >>>PUSHED".format(
        #        self.queue_name))

    def pop(self):
        try:
            # blocking pop
            message = copy.deepcopy(self.queue.get(block=True, timeout=5)) #maybe timeout isn't necessary
            self.queue.task_done()
            #logger.info(u"{:20}: <<<POPPED".format(
            #    self.queue_name))
        except Queue.Empty:
            message = None
        return message


class Worker(object):
    def run_in_loop(self):
        while True:
            self.run()

    def spawn_and_loop(self):
        t = threading.Thread(target=self.run_in_loop, name=self.name+"_thread")
        t.daemon = True
        t.start()    

class ProviderWorker(Worker):
    def __init__(self, provider, polling_interval, alias_queues, provider_queue, couch_queues, wrapper, myredis):
        self.provider = provider
        self.provider_name = provider.provider_name
        self.polling_interval = polling_interval 
        self.provider_queue = provider_queue
        self.alias_queues = alias_queues
        self.couch_queues = couch_queues
        self.wrapper = wrapper
        self.myredis = myredis
        self.name = self.provider_name+"_worker"

    # last variable is an artifact so it has same call signature as other callbacks
    def add_to_couch_queue_if_nonzero(self, 
            tiid, 
            new_content, 
            method_name, 
            analytics_credentials, 
            dummy_priority=None,
            dummy_already_run=None):
        # logger.info(u"In add_to_couch_queue_if_nonzero with {tiid}, {method_name}, {provider_name}".format(
        #    method_name=method_name, tiid=tiid, provider_name=self.provider_name))

        if not new_content:
            #logger.info(u"{:20}: Not writing to couch: empty {method_name} from {tiid} for {provider_name}".format(
            #    "provider_worker", method_name=method_name, tiid=tiid, provider_name=self.provider_name))     
            if method_name=="metrics":
                self.myredis.set_provider_finished(tiid, self.provider_name)
            return
        else:
            # logger.info(u"ADDING to couch queue {method_name} from {tiid} for {provider_name}".format(
            #     method_name=method_name, tiid=tiid, provider_name=self.provider_name))     
            couch_message = {
                "tiid": tiid, 
                "new_content": new_content, 
                "method_name": method_name,
                "analytics_credentials": analytics_credentials,                
                "provider_name": self.provider_name
            }

            couch_queue_index = tiid[0] #index them by the first letter in the tiid
            selected_couch_queue = self.couch_queues[couch_queue_index] 
            selected_couch_queue.push(couch_message)


    def add_to_alias_and_couch_queues(self, 
                tiid, 
                aliases_dict, 
                method_name, 
                analytics_credentials, 
                alias_providers_already_run):

        self.add_to_couch_queue_if_nonzero(tiid, aliases_dict, method_name, analytics_credentials)

        alias_message = {
                "tiid": tiid, 
                "aliases_dict": aliases_dict,
                "analytics_credentials": analytics_credentials,
                "alias_providers_already_run": alias_providers_already_run
            }        

        logger.info(u"Adding to alias queue tiid:{tiid} for {provider_name}".format(
            tiid=tiid, 
            provider_name=self.provider_name))     

        # always push to highest priority queue if we're already going
        self.alias_queues["high"].push(alias_message)


    @classmethod
    def wrapper(cls, tiid, input_aliases_dict, provider, method_name, analytics_credentials, aliases_providers_run, callback):
        #logger.info(u"{:20}: **Starting {tiid} {provider_name} {method_name} with {aliases}".format(
        #    "wrapper", tiid=tiid, provider_name=provider.provider_name, method_name=method_name, aliases=aliases))

        provider_name = provider.provider_name
        worker_name = provider_name+"_worker"

        input_alias_tuples = item_module.alias_tuples_from_dict(input_aliases_dict)
        method = getattr(provider, method_name)

        try:
            if provider.uses_analytics_credentials(method_name):
                method_response = method(input_alias_tuples, analytics_credentials=analytics_credentials)
            else:
                method_response = method(input_alias_tuples)
        except ProviderError:
            method_response = None
            logger.info(u"{:20}: **ProviderError {tiid} {method_name} {provider_name} ".format(
                worker_name, tiid=tiid, provider_name=provider_name.upper(), method_name=method_name.upper()))

        if method_name == "aliases":
            # update aliases to include the old ones too
            aliases_providers_run += [provider_name]
            if method_response:
                new_aliases_dict = item_module.alias_dict_from_tuples(method_response)
                new_canonical_aliases_dict = item_module.canonical_aliases(new_aliases_dict)
                response = item_module.merge_alias_dicts(new_canonical_aliases_dict, input_aliases_dict)
            else:
                response = input_aliases_dict
        else:
            response = method_response

        logger.info(u"{:20}: /biblio_print, RETURNED {tiid} {method_name} {provider_name} : {response}".format(
            worker_name, tiid=tiid, method_name=method_name.upper(), 
            provider_name=provider_name.upper(), response=response))

        callback(tiid, response, method_name, analytics_credentials, aliases_providers_run)

        try:
            del thread_count[provider_name][tiid+method_name]
        except KeyError:  # thread isn't there when we call wrapper in unit tests
            pass

        return response


    def run(self):
        num_active_threads_for_this_provider = len(thread_count[self.provider.provider_name])

        if num_active_threads_for_this_provider >= self.provider.max_simultaneous_requests:
            logger.info(u"{provider} has {num_provider} threads, so not spawning another yet".format(
                num_provider=num_active_threads_for_this_provider, provider=self.provider.provider_name.upper()))
            time.sleep(self.polling_interval) # let the provider catch up
            return

        provider_message = self.provider_queue.pop()
        if provider_message:
            #logger.info(u"POPPED from queue for {provider}".format(
            #    provider=self.provider_name))
            tiid = provider_message["tiid"]
            aliases_dict = provider_message["aliases_dict"]
            method_name = provider_message["method_name"]
            analytics_credentials = provider_message["analytics_credentials"]
            alias_providers_already_run = provider_message["alias_providers_already_run"]

            if (method_name == "metrics") and self.provider.provides_metrics:
                self.myredis.set_provider_started(tiid, self.provider.provider_name)

            if method_name == "aliases":
                callback = self.add_to_alias_and_couch_queues
            else:
                callback = self.add_to_couch_queue_if_nonzero

            #logger.info(u"BEFORE STARTING thread for {tiid} {method_name} {provider}".format(
            #    method_name=method_name.upper(), tiid=tiid, num=len(thread_count[self.provider.provider_name].keys()),
            #    provider=self.provider.provider_name.upper()))

            thread_count[self.provider.provider_name][tiid+method_name] = 1

            logger.info(u"{num_total} total threads, {num_provider} threads for {provider}".format(
                num_provider=num_active_threads_for_this_provider,
                num_total=threading.active_count(),
                provider=self.provider.provider_name.upper()))

            t = threading.Thread(target=ProviderWorker.wrapper, 
                args=(tiid, aliases_dict, self.provider, method_name, analytics_credentials, alias_providers_already_run, callback), 
                name=self.provider_name+"-"+method_name.upper()+"-"+tiid[0:4])
            t.start()
            return


class CouchWorker(Worker):
    def __init__(self, couch_queue, myredis, mydao):
        self.couch_queue = couch_queue
        self.myredis = myredis
        self.mydao = mydao
        self.name = self.couch_queue.queue_name + "_worker"

    @classmethod
    def update_item_with_new_aliases(cls, alias_dict, item_doc):
        if alias_dict == item_doc["aliases"]:
            item_doc = None
        else:
            item_obj = item_module.add_aliases_to_item_object(alias_dict, item_doc)

            merged_aliases = item_module.merge_alias_dicts(alias_dict, item_doc["aliases"])
            item_doc["aliases"] = merged_aliases
        return(item_doc)

    @classmethod
    def update_item_with_new_biblio(cls, new_biblio_dict, item_doc):
        # return None if no changes
        # don't change if biblio already there

        response = item_module.get_biblio_to_update(item_doc["biblio"], new_biblio_dict)
        if response:
            item_doc["biblio"] = response
            item_obj = item_module.add_biblio_to_item_object(new_biblio_dict, item_doc)
        else:
            item_doc = None

        return(item_doc)


    @classmethod
    def update_item_with_new_metrics(cls, metric_name, metrics_method_response, item_doc):
        item_doc = item_module.add_metrics_data(metric_name, metrics_method_response, item_doc)
        item_obj = item_module.add_metric_to_item_object(metric_name, metrics_method_response, item_doc)
        return(item_doc)        


    def run(self):
        couch_message = self.couch_queue.pop()
        if couch_message:
            tiid = couch_message["tiid"]
            new_content = couch_message["new_content"]
            method_name = couch_message["method_name"]
            analytics_credentials = couch_message["analytics_credentials"]
            provider_name = couch_message["provider_name"]

            if not new_content:
                logger.info(u"{:20}: blank doc, nothing to save".format(
                    self.name))
            else:
                # don't need it with metrics for this purpose
                item_obj = item_module.Item.query.get(tiid)
                item = item_obj.as_old_doc()

                if not item:
                    if method_name=="metrics":
                        self.myredis.set_provider_finished(tiid, provider_name)
                    logger.error(u"Empty item from couch for tiid {tiid}, can't save {method_name}".format(
                        tiid=tiid, method_name=method_name))
                    return
                if method_name=="aliases":
                    updated_item = self.update_item_with_new_aliases(new_content, item)
                elif method_name=="biblio":
                    updated_item = self.update_item_with_new_biblio(new_content, item)
                elif method_name=="metrics":
                    updated_item = item
                    for metric_name in new_content:
                        updated_item = self.update_item_with_new_metrics(metric_name, new_content[metric_name], updated_item)
                else:
                    logger.warning(u"ack, supposed to save something i don't know about: " + str(new_content))
                    updated_item = None

                # now that is has been updated it, change last_modified and save
                if updated_item:
                    updated_item["last_modified"] = datetime.datetime.utcnow().isoformat()
                    logger.info(u"{:20}: added {method_name}, saving item {tiid}".format(
                        self.name, method_name=method_name, tiid=tiid))
                    db.session.merge(item_obj)

                if method_name=="metrics":
                    self.myredis.set_provider_finished(tiid, provider_name) # have to do this after the item save
                db.session.remove()
        else:
            #time.sleep(0.1)  # is this necessary?
            pass


class Backend(Worker):
    def __init__(self, alias_queues, provider_queues, couch_queues, myredis):
        self.alias_queues = alias_queues
        self.provider_queues = provider_queues
        self.couch_queues = couch_queues
        self.myredis = myredis
        self.name = "Backend"

    @classmethod
    def sniffer(cls, item_aliases, aliases_providers_run, provider_config=default_settings.PROVIDERS):
        # default to nothing
        aliases_providers = []
        biblio_providers = []
        metrics_providers = []

        all_metrics_providers = [provider.provider_name for provider in 
                        ProviderFactory.get_providers(provider_config, "metrics")]
        (genre, host) = item_module.decide_genre(item_aliases)

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
                biblio_providers = ["crossref", "pubmed", "webpage"]
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

    def providers_too_busy(self, max_requests=10):
        for provider_name in thread_count:
            num_active_threads_for_this_provider = len(thread_count[provider_name])
            if num_active_threads_for_this_provider >= max_requests:
                return True
        return False

    def run(self):
        # go through alias_queues, with highest priority first
        alias_message = self.alias_queues["high"].pop()
        if not alias_message and not self.providers_too_busy():
            alias_message = self.alias_queues["low"].pop()

        if alias_message:
            logger.info(u"/biblio_print, ALIAS_MESSAGE said {alias_message}".format(
               alias_message=alias_message))
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
                    self.provider_queues[provider_name].push(provider_message)
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


    # these need to match the tiid alphabet defined in models:
    couch_queues = {}
    for i in "abcdefghijklmnopqrstuvwxyz1234567890":
        couch_queues[i] = PythonQueue(i+"_couch_queue")
        couch_worker = CouchWorker(couch_queues[i], myredis, mydao)
        couch_worker.spawn_and_loop() 
        logger.info(u"launched backend couch worker with {i}_couch_queue".format(
            i=i))


    polling_interval = 0.1   # how many seconds between polling to talk to provider
    provider_queues = {}
    providers = ProviderFactory.get_providers(default_settings.PROVIDERS)
    for provider in providers:
        provider_queues[provider.provider_name] = PythonQueue(provider.provider_name+"_queue")
        provider_worker = ProviderWorker(
            provider, 
            polling_interval, 
            alias_queues,
            provider_queues[provider.provider_name], 
            couch_queues,
            ProviderWorker.wrapper,
            myredis)
        provider_worker.spawn_and_loop()

    backend = Backend(alias_queues, provider_queues, couch_queues, myredis)
    try:
        backend.run_in_loop() # don't need to spawn this one
    except (KeyboardInterrupt, SystemExit): 
        # this approach is per http://stackoverflow.com/questions/2564137/python-how-to-terminate-a-thread-when-main-program-ends
        sys.exit()
 
if __name__ == "__main__":
    main()
