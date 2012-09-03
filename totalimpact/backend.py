import os, time, json, logging, threading, Queue, copy, sys
import librato
from collections import defaultdict

from totalimpact import dao, tiredis, default_settings
from totalimpact.models import ItemFactory
from totalimpact.providers.provider import ProviderFactory, ProviderError

logger = logging.getLogger('ti.backend')
logger.setLevel(logging.DEBUG)

mylibrato = librato.LibratoConnection(os.environ["LIBRATO_METRICS_USER"], os.environ["LIBRATO_METRICS_TOKEN"])

def get_or_create(metric_type, name, description):
    if metric_type=="counter":
        try:
            metric = mylibrato.get_counter(name)
        except librato.exceptions.ClientError:
            metric = mylibrato.create_counter(name, description)
    else:
        try:
            metric = mylibrato.get_gauge(name)
        except librato.exceptions.ClientError:
            metric = mylibrato.create_gauge(name, description)
    return metric

thread_count = defaultdict(int)
librato_provider_thread_start = get_or_create("guage", "provider_thread_start", "+1 when a provider thread is started")
librato_provider_thread_end = get_or_create("guage", "provider_thread_end", "+1 when a provider thread is ended")
librato_provider_thread_run_duration = get_or_create("gauge", "provider_thread_run_duration", "elapsed time for a provider thread to run")
librato_provider_thread_launch_duration = get_or_create("gauge", "provider_thread_launch_duration", "elapsed time for a provider thread to launch")
librato_provider_thread_count = get_or_create("gauge", "provider_thread_count", "number of threads running")


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
        self.name = "worker_"+self.provider_name

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
        worker_name = "worker_"+provider_name
        start_time = time.time()

        logger.info("{:20}: STARTING WRAPPER for {tiid} {method_name} {provider}".format(
            worker_name, method_name=method_name.upper(), tiid=tiid,
            provider=provider.provider_name.upper()))

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

        logger.info("{:20}: ENDING WRAPPER for {tiid} {method_name} {provider}, finished in {elapsed} seconds".format(
            worker_name, method_name=method_name.upper(), tiid=tiid,
            provider=provider_name.upper(), elapsed=time.time()-start_time))

        librato_provider_thread_run_duration.add(time.time()-start_time, source=provider_name)
        librato_provider_thread_end.add(1, source=provider_name)
        thread_count[provider_name] += -1
        librato_provider_thread_count.add(thread_count[provider_name], source=provider_name)

        return response

    def run(self):
        provider_message = self.provider_queue.pop()
        if provider_message:
            logger.info("POPPED from queue for {provider}".format(
                provider=self.provider_name))
            (tiid, alias_dict, method_name, aliases_providers_run) = provider_message
            if method_name == "aliases":
                callback = self.add_to_alias_and_couch_queues
            else:
                callback = self.add_to_couch_queue_if_nonzero

            start_time = time.time()

            logger.info("BEFORE STARTING thread for {tiid} {method_name} {provider}".format(
                method_name=method_name.upper(), tiid=tiid,
                provider=self.provider.provider_name.upper()))

            librato_provider_thread_start.add(1, source=self.provider.provider_name)
            thread_count[self.provider.provider_name] += 1
            librato_provider_thread_count.add(thread_count[self.provider.provider_name], source=self.provider.provider_name)

            t = threading.Thread(target=ProviderWorker.wrapper, 
                args=(tiid, alias_dict, self.provider, method_name, aliases_providers_run, callback), 
                name=self.provider_name+"-"+method_name.upper()+"-"+tiid[0:4])
            t.start()

            logger.info("LAUNCHED THREAD for {tiid} {method_name} {provider} took {elapsed} seconds".format(
                tiid=tiid, elapsed=time.time() - start_time, method_name=method_name.upper(), 
                provider=self.provider.provider_name.upper()))

            librato_provider_thread_launch_duration.add(time.time()-start_time, source=self.provider.provider_name)

            # sleep to give the provider a rest :)
            time.sleep(self.polling_interval)



class CouchWorker(Worker):
    def __init__(self, couch_queue, myredis, mydao):
        self.couch_queue = couch_queue
        self.myredis = myredis
        self.mydao = mydao
        self.name = "worker_" + self.couch_queue.queue_name 

    def update_item_with_new_aliases(self, alias_dict, item):
        if alias_dict == item["aliases"]:
            item = None
        else:
            merged_aliases = ItemFactory.merge_alias_dicts(alias_dict, item["aliases"])
            item["aliases"] = merged_aliases
            #logger.info("{:20}: added aliases, saving item {item}".format(
            #    self.name, item=item))
        return(item)

    def update_item_with_new_biblio(self, biblio_dict, item):
        # return None if no changes
        # don't change if biblio already there
        if item["biblio"]:
            #logger.info("{:20}: {tiid} already had biblio, not saving".format(
            #    self.name, tiid=item["_id"]))
            item = None
        else:
            item["biblio"] = biblio_dict
            #logger.info("{:20}: added biblio, saving item {item}".format(
            #    self.name, item=item))
        return(item)

    def run(self):
        couch_message = self.couch_queue.pop()
        if couch_message:
            (tiid, new_content, method_name) = couch_message
            if not new_content:
                logger.info("{:20}: blank doc, nothing to save".format(
                    self.name))
            else:
                item = self.mydao.get(tiid)
                if method_name=="aliases":
                    updated_item = self.update_item_with_new_aliases(new_content, item)
                    if updated_item:
                        logger.info("{:20}: added aliases, saving item {tiid}".format(
                            self.name, tiid=tiid))
                        self.mydao.save(updated_item)
                elif method_name=="biblio":
                    updated_item = self.update_item_with_new_biblio(new_content, item)
                    if updated_item:
                        logger.info("{:20}: added biblio, saving item {tiid}".format(
                            self.name, tiid=tiid))
                        self.mydao.save(updated_item)
                elif method_name=="metrics":
                    for metric_name in new_content:
                        snap = ItemFactory.build_snap(tiid, new_content[metric_name], metric_name)
                        logger.info("{:20}: added metrics to {tiid}, saving snap {snap}".format(
                            self.name, tiid=tiid, snap=snap["_id"]))
                        self.mydao.save(snap)
                        provider_name = metric_name.split(":")[0]
                    self.myredis.decr_num_providers_left(tiid, provider_name)

                else:
                    logger.info("{:20}: ack, supposed to save something i don't know about: " + str(new_content))
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
            if has_alias_urls:
                # aliases are all done
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
            logger.info("{:20}: alias_message said {alias_message}".format(
                "Backend.run", alias_message=alias_message))            
            (tiid, alias_dict, aliases_providers_run) = alias_message

            relevant_provider_names = self.sniffer(alias_dict, aliases_providers_run)
            logger.info("{:20}: for {tiid} sniffer got input {alias_dict}".format(
                "Backend", tiid=tiid, alias_dict=alias_dict))
            logger.info("{:20}: for {tiid} sniffer returned {providers}".format(
                "Backend", tiid=tiid, providers=relevant_provider_names))

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
    mydao.update_design_doc()

    myredis = tiredis.from_url(os.getenv("REDISTOGO_URL"))
    alias_queue = RedisQueue("aliasqueue", myredis)

    # these need to match the tiid alphabet defined in models:
    couch_queues = {}
    for i in "abcdefghijklmnopqrstuvwxyz1234567890":
        couch_queues[i] = PythonQueue("couch_queue_"+i)
        couch_worker = CouchWorker(couch_queues[i], myredis, mydao)
        couch_worker.spawn_and_loop() 
        logger.info("{:20}: launched backend couch worker with couch_queue_{i}".format(
            "Backend", i=i))


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
