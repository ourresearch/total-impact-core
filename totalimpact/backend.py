#!/usr/bin/env python

import os, time, json, logging, threading, Queue, copy, sys, datetime
from collections import defaultdict

from totalimpact import dao, tiredis, default_settings
from totalimpact.models import ItemFactory
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
        #logger.info("{:20}: >>>PUSHING to redis {message_json}".format(
        #    self.name, message_json=message_json))        
        self.myredis.lpush(self.queue_name, message_json)

    def pop(self):
        #blocking pop
        message = None
        received = self.myredis.brpop([self.queue_name], timeout=5) #maybe timeout not necessary
        if received:
            queue, message_json = received
            try:
                message = json.loads(message_json) 
                logger.info("{:20}: <<<POPPED from redis, {message}".format(
                    self.name, message=message))        
            except TypeError, KeyError:
                logger.info("{:20}: error processing redis message {message_json}".format(
                    self.name, message_json=message_json))
        return message


class PythonQueue(object):
    def __init__(self, queue_name):
        self.queue_name = queue_name
        self.queue = Queue.Queue()

    def push(self, message):
        self.queue.put(copy.deepcopy(message))
        #logger.info("{:20}: >>>PUSHED".format(
        #        self.queue_name))

    def pop(self):
        try:
            # blocking pop
            message = copy.deepcopy(self.queue.get(block=True, timeout=5)) #maybe timeout isn't necessary
            self.queue.task_done()
            #logger.info("{:20}: <<<POPPED".format(
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
    def __init__(self, provider, polling_interval, alias_queue, provider_queue, couch_queues, wrapper, myredis):
        self.provider = provider
        self.provider_name = provider.provider_name
        self.polling_interval = polling_interval 
        self.provider_queue = provider_queue
        self.alias_queue = alias_queue
        self.couch_queues = couch_queues
        self.wrapper = wrapper
        self.myredis = myredis
        self.name = self.provider_name+"_worker"

    # last variable is an artifact so it has same call signature as other callbacks
    def add_to_couch_queue_if_nonzero(self, tiid, new_content, method_name, dummy=None):
        if not new_content:
            #logger.info("{:20}: Not writing to couch: empty {method_name} from {tiid} for {provider_name}".format(
            #    "provider_worker", method_name=method_name, tiid=tiid, provider_name=self.provider_name))     
            if method_name=="metrics":
                self.myredis.decr_num_providers_left(tiid, "(unknown)")
            return
        else:
            logger.info("Adding to couch queue {method_name} from {tiid} for {provider_name}".format(
                method_name=method_name, tiid=tiid, provider_name=self.provider_name))     
            couch_message = (tiid, new_content, method_name)
            couch_queue_index = tiid[0] #index them by the first letter in the tiid
            selected_couch_queue = self.couch_queues[couch_queue_index] 
            selected_couch_queue.push(couch_message)

    def add_to_alias_and_couch_queues(self, tiid, alias_dict, method_name, aliases_providers_run):
        self.add_to_couch_queue_if_nonzero(tiid, alias_dict, method_name)
        alias_message = [tiid, alias_dict, aliases_providers_run]
        self.alias_queue.push(alias_message)

    @classmethod
    def wrapper(cls, tiid, input_aliases_dict, provider, method_name, aliases_providers_run, callback):
        #logger.info("{:20}: **Starting {tiid} {provider_name} {method_name} with {aliases}".format(
        #    "wrapper", tiid=tiid, provider_name=provider.provider_name, method_name=method_name, aliases=aliases))

        provider_name = provider.provider_name
        worker_name = provider_name+"_worker"

        input_alias_tuples = ItemFactory.alias_tuples_from_dict(input_aliases_dict)
        method = getattr(provider, method_name)

        try:
            method_response = method(input_alias_tuples)
        except ProviderError:
            method_response = None
            logger.info("{:20}: **ProviderError {tiid} {method_name} {provider_name} ".format(
                worker_name, tiid=tiid, provider_name=provider_name.upper(), method_name=method_name.upper()))

        if method_name == "aliases":
            # update aliases to include the old ones too
            aliases_providers_run += [provider_name]
            if method_response:
                new_aliases_dict = ItemFactory.alias_dict_from_tuples(method_response)
                response = ItemFactory.merge_alias_dicts(new_aliases_dict, input_aliases_dict)
            else:
                response = input_aliases_dict
        else:
            response = method_response

        logger.info("{:20}: RETURNED {tiid} {method_name} {provider_name} : {response}".format(
            worker_name, tiid=tiid, method_name=method_name.upper(), 
            provider_name=provider_name.upper(), response=response))

        callback(tiid, response, method_name, aliases_providers_run)

        try:
            del thread_count[provider_name][tiid+method_name]
        except KeyError:  # thread isn't there when we call wrapper in unit tests
            pass

        return response

    def run(self):
        provider_message = self.provider_queue.pop()
        if provider_message:
            #logger.info("POPPED from queue for {provider}".format(
            #    provider=self.provider_name))
            (tiid, alias_dict, method_name, aliases_providers_run) = provider_message
            if method_name == "aliases":
                callback = self.add_to_alias_and_couch_queues
            else:
                callback = self.add_to_couch_queue_if_nonzero

            #logger.info("BEFORE STARTING thread for {tiid} {method_name} {provider}".format(
            #    method_name=method_name.upper(), tiid=tiid, num=len(thread_count[self.provider.provider_name].keys()),
            #    provider=self.provider.provider_name.upper()))

            thread_count[self.provider.provider_name][tiid+method_name] = 1

            logger.info("NUMBER of {provider} threads = {num_provider}, all threads = {num_total}".format(
                num_provider=len(thread_count[self.provider.provider_name]),
                num_total=threading.active_count(),
                provider=self.provider.provider_name.upper()))

            t = threading.Thread(target=ProviderWorker.wrapper, 
                args=(tiid, alias_dict, self.provider, method_name, aliases_providers_run, callback), 
                name=self.provider_name+"-"+method_name.upper()+"-"+tiid[0:4])
            t.start()

            # sleep to give the provider a rest :)
            time.sleep(self.polling_interval)



class CouchWorker(Worker):
    def __init__(self, couch_queue, myredis, mydao):
        self.couch_queue = couch_queue
        self.myredis = myredis
        self.mydao = mydao
        self.name = self.couch_queue.queue_name + "_worker"

    @classmethod
    def update_item_with_new_aliases(cls, alias_dict, item):
        if alias_dict == item["aliases"]:
            item = None
        else:
            merged_aliases = ItemFactory.merge_alias_dicts(alias_dict, item["aliases"])
            item["aliases"] = merged_aliases
        return(item)

    @classmethod
    def update_item_with_new_biblio(cls, biblio_dict, item):
        # return None if no changes
        # don't change if biblio already there
        if item["biblio"]:
            item = None
        else:
            item["biblio"] = biblio_dict
        return(item)

    @classmethod
    def update_item_with_new_snap(cls, snap, item):
        item = ItemFactory.add_snap_data(item, snap)  #note the flipped order.  hrm.
        return(item)        

    def decr_num_providers_left(self, metric_name, tiid):
        provider_name = metric_name.split(":")[0]
        if not provider_name:
            provider_name = "(unknown)"
        self.myredis.decr_num_providers_left(tiid, provider_name)

    def run(self):
        couch_message = self.couch_queue.pop()
        if couch_message:
            (tiid, new_content, method_name) = couch_message
            if not new_content:
                logger.info("{:20}: blank doc, nothing to save".format(
                    self.name))
            else:
                item = self.mydao.get(tiid)
                if not item:
                    if method_name=="metrics":
                        self.myredis.decr_num_providers_left(tiid, "(unknown)")
                    logger.error("Empty item from couch for tiid {tiid}, can't save {method_name}".format(
                        tiid=tiid, method_name=method_name))
                    return
                if method_name=="aliases":
                    updated_item = self.update_item_with_new_aliases(new_content, item)
                elif method_name=="biblio":
                    updated_item = self.update_item_with_new_biblio(new_content, item)
                elif method_name=="metrics":
                    # this is the loop we are going to keep.  add all the snaps into the item.
                    updated_item = item
                    for metric_name in new_content:
                        snap = ItemFactory.build_snap(tiid, new_content[metric_name], metric_name)
                        updated_item = self.update_item_with_new_snap(snap, updated_item)
                else:
                    logger.warning("ack, supposed to save something i don't know about: " + str(new_content))
                    updated_item = None

                # now that is has been updated it, change last_modified and save
                if updated_item:
                    updated_item["last_modified"] = datetime.datetime.now().isoformat()
                    logger.info("{:20}: added {method_name}, saving item {tiid}".format(
                        self.name, method_name=method_name, tiid=tiid))
                    self.mydao.save(updated_item)

                if method_name=="metrics":
                    self.decr_num_providers_left(metric_name, tiid) # have to do this after the item save
        else:
            #time.sleep(0.1)  # is this necessary?
            pass


class Backend(Worker):
    def __init__(self, alias_queue, provider_queues, couch_queues, myredis):
        self.alias_queue = alias_queue
        self.provider_queues = provider_queues
        self.couch_queues = couch_queues
        self.myredis = myredis
        self.name = "Backend"

    @classmethod
    def sniffer(cls, item_aliases, aliases_providers_run, provider_config=default_settings.PROVIDERS):
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

        all_metrics_providers = [provider.provider_name for provider in 
                        ProviderFactory.get_providers(provider_config, "metrics")]
        genre = ItemFactory.decide_genre(item_aliases)
        has_alias_urls = "url" in item_aliases

        if (genre == "article"):
            if not "pubmed" in aliases_providers_run:
                aliases_providers = ["pubmed"]
            elif not "crossref" in aliases_providers_run:
                aliases_providers = ["crossref"]
            else:
                metrics_providers = all_metrics_providers
                biblio_providers = ["pubmed", "crossref"]
        else:
            # relevant alias and biblio providers are always the same
            relevant_providers = simple_products_provider_lookup[genre]
            # if all the relevant providers have already run, then all the aliases are done
            # or if it already has urls
            if has_alias_urls or set(relevant_providers).issubset(set(aliases_providers_run)):
                metrics_providers = all_metrics_providers
                biblio_providers = relevant_providers
            else:
                aliases_providers = relevant_providers

        return({
            "aliases":aliases_providers,
            "biblio":biblio_providers,
            "metrics":metrics_providers})

    def run(self):
        alias_message = self.alias_queue.pop()
        if alias_message:
            logger.info("alias_message said {alias_message}".format(
                alias_message=alias_message))            
            (tiid, alias_dict, aliases_providers_run) = alias_message

            relevant_provider_names = self.sniffer(alias_dict, aliases_providers_run)
            logger.info("backend for {tiid} sniffer got input {alias_dict}".format(
                tiid=tiid, alias_dict=alias_dict))
            logger.info("backend for {tiid} sniffer returned {providers}".format(
                tiid=tiid, providers=relevant_provider_names))

            # list out the method names so they are run in that priority, biblio before metrics
            for method_name in ["aliases", "biblio", "metrics"]:
                for provider_name in relevant_provider_names[method_name]:

                    provider_message = (tiid, alias_dict, method_name, aliases_providers_run)
                    self.provider_queues[provider_name].push(provider_message)
        else:
            #time.sleep(0.1)  # is this necessary?
            pass



def main():
    mydao = dao.Dao(os.environ["CLOUDANT_URL"], os.environ["CLOUDANT_DB"])

    myredis = tiredis.from_url(os.getenv("REDISTOGO_URL"))
    alias_queue = RedisQueue("aliasqueue", myredis)
    # to clear alias_queue:
    #import redis, os
    #myredis = redis.from_url(os.getenv("REDISTOGO_URL"))
    #myredis.delete(["aliasqueue"])


    # these need to match the tiid alphabet defined in models:
    couch_queues = {}
    for i in "abcdefghijklmnopqrstuvwxyz1234567890":
        couch_queues[i] = PythonQueue(i+"_couch_queue")
        couch_worker = CouchWorker(couch_queues[i], myredis, mydao)
        couch_worker.spawn_and_loop() 
        logger.info("launched backend couch worker with {i}_couch_queue".format(
            i=i))


    polling_interval = 0.1   # how many seconds between polling to talk to provider
    provider_queues = {}
    providers = ProviderFactory.get_providers(default_settings.PROVIDERS)
    for provider in providers:
        provider_queues[provider.provider_name] = PythonQueue(provider.provider_name+"_queue")
        provider_worker = ProviderWorker(
            provider, 
            polling_interval, 
            alias_queue,
            provider_queues[provider.provider_name], 
            couch_queues,
            ProviderWorker.wrapper,
            myredis)
        provider_worker.spawn_and_loop()

    backend = Backend(alias_queue, provider_queues, couch_queues, myredis)
    try:
        backend.run_in_loop() # don't need to spawn this one
    except (KeyboardInterrupt, SystemExit): 
        # this approach is per http://stackoverflow.com/questions/2564137/python-how-to-terminate-a-thread-when-main-program-ends
        sys.exit()
 
if __name__ == "__main__":
    main()
