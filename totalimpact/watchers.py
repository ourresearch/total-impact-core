import threading, time, sys
from totalimpact.config import Configuration
from totalimpact.queue import AliasQueue, MetricsQueue
from totalimpact.providers.provider import ProviderFactory, ProviderConfigurationError

from totalimpact.tilogging import logging
log = logging.getLogger(__name__)

class Watchers(object):
    
    def __init__(self, config_path):
        self.threads = []
        self.config = Configuration(config_path)
        self.providers = ProviderFactory.get_providers()
        
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
           
class StoppableThread(threading.Thread):
    def __init__(self):
        super(StoppableThread, self).__init__()
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

class QueueConsumer(object):

    def __init__(self, queue):
        self.queue = queue
    
    def first(self):
        # get the first item on the queue (waiting until there is
        # such a thing if necessary)
        item = None
        while item is None and not self.stopped():
            item = self.queue.first()
            if item is None:
                # if the queue is empty, wait 0.5 seconds before checking
                # again
                time.sleep(0.5)
            return item

class ProvidersAliasThread(StoppableThread, QueueConsumer):
    def __init__(self, providers, config):
        StoppableThread.__init__(self)
        QueueConsumer.__init__(self, AliasQueue())
        self.providers = providers
        self.config = config
        
    def run(self):
        while not self.stopped():
            # get the first item on the queue - this waits until
            # there is something to return
            item = self.first()
            
            for p in self.providers:
                try:
                    item = p.aliases(item)
                    self.queue.save_and_unqueue(item)
                    
                    # FIXME: still debugging, but remove soon
                    print item
                except NotImplementedError:
                    continue
                    
            # FIXME: we need a better sleep mechanism which allows
            # the thread to be stopped while it is sleeping
            time.sleep(self.sleep_time())
            
    def sleep_time(self):
        # just keep punting through the aliases as fast as possible
        # FIXME: ultimately we need a better mechanism to throttle
        # the alias requests, like skipping providers which are over
        # limit
        return 0

class ProviderMetricsThread(StoppableThread, QueueConsumer):

    def __init__(self, provider, config):
        StoppableThread.__init__(self)
        QueueConsumer.__init__(self, MetricsQueue())
        self.provider = provider
        self.config = config
        self.queue.provider = self.provider.id

    def run(self):
        while not self.stopped():
            start = time.time()
            
            # get the first item on the queue - this waits until
            # there is something to return
            item = self.first()
            
            # if we get to here, an Alias has been popped off the queue
            item = self.provider.metrics(item)
            
            # FIXME: metrics requests might throw errors which cause
            # a None to be returned from the metrics request.  If that's
            # the case then don't save, but we should probably have a 
            # better error handling routine
            if item is not None:
                # store the metrics in the database
                self.queue.save_and_unqueue(item)
                
                # FIXME: still debugging, but remove soon
                print metrics
            
            # FIXME: we need to take into account dead time which is longer
            # than the desired sleep time (i.e. dead time that we can carry
            # over
            # FIXME: we need a better sleep mechanism which allows
            # the thread to be stopped while it is sleeping
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
