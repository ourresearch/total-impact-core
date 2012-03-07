import threading, time, sys
from totalimpact.config import Configuration
from totalimpact.queue import Queue
from totalimpact.providers.provider import ProviderFactory, ProviderConfigurationError

from totalimpact.tilogging import logging
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
        
        alias_thread = ProvidersAliasThread(self.providers, self.config)
        alias_thread.start()
        self.threads.append(alias_thread)
        
        # now monitor our threads and the system for interrupts,
        # and manage a clean exit
        try:
            while True:
                # just spin our wheels waiting for interrupts
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            log.info("Interrupted ... exiting ...")
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
                log.error("Unable to configure provider ... skipping " + str(p))
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
    def __init__(self, providers, config):
        super(ProvidersAliasThread, self).__init__()
        self.providers = providers
        self.config = config
        self.queue = Queue("aliases")
        
    def run(self):
        while not self.stopped():
            # check queue
            alias_object = None
            while alias_object is None and not self.stopped():
                alias_object = self.queue.next()
            
            for p in self.providers:
                try:
                    aliases = p.aliases(alias_object)
                    
                    # FIXME: what to do with these aliases now?
                    print aliases
                except NotImplementedError:
                    continue
            time.sleep(self.sleep_time())
            
    def sleep_time(self):
        # just keep punting through the aliases as fast as possible
        # FIXME: ultimately we need a better mechanism to throttle
        # the alias requests, like skipping providers which are over
        # limit
        return 0

class ProviderMetricsThread(StoppableThread):

    def __init__(self, provider, config):
        super(ProviderMetricsThread, self).__init__()
        self.provider = provider
        self.config = config
        self.queue = Queue("metrics", self.provider.id)

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