import logging, threading, time
log = logging.getLogger(__name__)

class Watchers(object):
    
    def run(self):
        threads = []
        #config = self.get_config()
        #providers = self.get_providers()
        #for p in providers:
        #    threads.append(ProviderMetricsThread(p, config).run()) # start thread
        #threads.append(ProviderAliasThread(providers).run())
        alias_thread = ProvidersAliasThread([])
        alias_thread.start()
        
        metrics_thread = ProviderMetricsThread(None, None)
        metrics_thread.start()
        
        try:
            while True:
                # just spin our wheels waiting for interrupts
                time.sleep(0.5)
        except (KeyboardInterrupt, SystemExit):
            alias_thread.stop()
            metrics_thread.stop()
            
            print "Interrupted ... exiting"
            alias_thread.join(5)
            metrics_thread.join(5)
            
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
                p.aliases(alias_object)
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
            # time.sleep(self.provider.sleep_time())
            time.sleep(self.sleep_time())
            # check queue
            alias_object = None # get this off the queue
            # metrics = self.provider.metrics(alias_object)
            print "metrics"
  
    def sleep_time(self):
        return 3
  
if __name__ == "__main__":
    Watchers().run()