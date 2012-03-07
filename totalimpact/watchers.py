import logging, threading, time, sys
from totalimpact.config import Configuration
from totalimpact.queue import Queue
from totalimpact.providers.provider import ProviderFactory, ProviderConfigurationError

log = logging.getLogger(__name__)

class Watchers(object):
    
    def __init__(self, config_path):
        self.threads = []
        self.config = Configuration(config_path)
        self.providers = self._get_providers()
        
    def run(self):
        for p in self.providers:
            if not p.provides_metrics():
                continue
            # create and start the metrics threads
            t = ProviderMetricsThread(p, self.config)
            t.start()
            self.threads.append(t)
        
        alias_thread = ProvidersAliasThread(self.providers)
        alias_thread.start()
        self.threads.append(alias_thread)
        
        # now monitor our threads and the system for interrupts,
        # and manage a clean exit
        try:
            while True:
                # just spin our wheels waiting for interrupts
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            print "Interrupted ... exiting ..."
            for t in self.threads:
                t.stop()
       
       # FIXME: do we need to join() the thread?
       
    def _get_providers(self):
        providers = []
        for p in self.config.providers:
            try:
                prov = ProviderFactory.get_provider(p, self.config)
                providers.append(prov)
            except ProviderConfigurationError:
                print "WARN: Unable to configure provider ... skipping ", p
        return providers
    
class StoppableThread(threading.Thread):
    def __init__(self):
        super(StoppableThread, self).__init__()
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

class ProvidersAliasThread(StoppableThread):
    def __init__(self, providers):
        super(ProvidersAliasThread, self).__init__()
        self.providers = providers
        self.config = None
        
    def run(self):
        while not self.stopped():
            alias_object = None # get this off the queue
            for p in self.providers:
                try:
                    p.aliases(alias_object)
                except NotImplementedError:
                    continue
            time.sleep(self.sleep_time())
            
    def sleep_time(self):
        return 1

class ProviderMetricsThread(StoppableThread):

    def __init__(self, provider, config):
        super(ProviderMetricsThread, self).__init__()
        self.provider = provider
        self.config = config
        self.queue = Queue()

    def run(self):
        while not self.stopped():
            start = time.time()
            
            # check queue
            alias_object = None
            while alias_object is None and not self.stopped():
                alias_object = self.queue.next()
            
            # if we get to here, an Alias has been popped off the queue
            metrics = self.provider.metrics(alias_object)
            
            if metrics is not None:
                # store the metrics in the database
                # TODO
                
                # remove the alias_object from the queue
                self.queue.remove(alias_object)
                
                # FIXME: just for the time being
                print metrics
            
            # go to sleep for a time specified by the provider which
            # is dependent on how long this request took in the first place
            time.sleep(self.provider.sleep_time(self._get_dead_time(start)))
            
    def _get_dead_time(self, start):
        end = time.time()
        return end - start
  
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Please supply the path to the configuration file"
    else:
        Watchers(sys.argv[1]).run()