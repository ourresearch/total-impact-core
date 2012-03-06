import logging, threading, time, sys
from config import Configuration
from model import Alias

log = logging.getLogger(__name__)

class Watchers(object):
    
    def __init__(self, config_path):
        self.threads = []
        self.config = Configuration(config_path)
        self.providers = self._get_providers()
        
    def run(self):
        for p in self.providers:
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
            conf = Configuration(config_file=p['config'])
            klazz = self.config.get_class(p['class'])
            providers.append(klazz(conf))
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
            # sleep first, since otherwise this delays stoppage
            time.sleep(self.sleep_time())
            alias_object = None # get this off the queue
            for p in self.providers:
                # FIXME: will currently throw a NotImplementedError
                #p.aliases(alias_object)
                pass
            print "aliases"
            
    def sleep_time(self):
        return 1

class ProviderMetricsThread(StoppableThread):

    def __init__(self, provider, config):
        super(ProviderMetricsThread, self).__init__()
        self.provider = provider
        self.config = config

    def run(self):
        while not self.stopped():
            # sleep first, since otherwise this delays stoppage
            time.sleep(self.provider.sleep_time())
            # check queue
            alias_object = None # get this off the queue
            
            # FIXME: just for testing
            alias_object = Alias([("doi", "10.1371/journal.pcbi.1000361"), ("url", "http://cottagelabs.com")])
            metrics = self.provider.metrics(alias_object)
            print metrics
  
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Please supply the path to the configuration file"
    else:
        Watchers(sys.argv[1]).run()