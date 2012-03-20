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
        self.providers = ProviderFactory.get_providers(self.config)
        
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
       # it would seem not, but don't forget to keep an eye on this
           
class StoppableThread(threading.Thread):
    def __init__(self):
        super(StoppableThread, self).__init__()
        self._stop = threading.Event()
        self.sleeping = False

    def run(self):
        # NOTE: subclasses MUST override this - this behaviour is
        # only for testing purposes
        
        # go into a restless but persistent sleep (in 60 second
        # batches)
        while not self.stopped():
            self._interruptable_sleep(60)

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()
    
    def _interruptable_sleep(self, duration, increment=0.5):
        self.sleeping = True
        if duration <= 0:
            return
        slept = 0
        while not self.stopped() and slept < duration:
            snooze = increment if duration - slept > increment else duration - slept
            time.sleep(snooze)
            slept += snooze
        self.sleeping = False

class QueueConsumer(StoppableThread):

    def __init__(self, queue):
        StoppableThread.__init__(self)
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

# NOTE: provider aliases does not throttle or take into account
# provider sleep times.  This is fine for the time being, as 
# aliasing is an urgent request.  The provider should count the
# requests as they happen, so that the metrics thread can keep itself
# in check to throttle the api requests.
class ProvidersAliasThread(QueueConsumer):
    def __init__(self, providers, config):
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
                    
                    # FIXME: queue object is not yet working
                    #self.queue.save_and_unqueue(item)
                except NotImplementedError:
                    continue
                    
            self._interruptable_sleep(self.sleep_time())
            
    def sleep_time(self):
        # just keep punting through the aliases as fast as possible for the time being
        return 0

class ProviderMetricsThread(QueueConsumer):

    def __init__(self, provider, config):
        QueueConsumer.__init__(self, MetricsQueue())
        self.provider = provider
        self.config = config
        self.queue.provider = self.provider.id

    def run(self):
        while not self.stopped():
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
                
                # FIXME: queue object is not yet working
                #self.queue.save_and_unqueue(item)
                pass
            
            # the provider will return a sleep time which may be negative
            sleep_time = self.provider.sleep_time()
            
            # sleep
            self._interruptable_sleep(sleep_time)
  
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Please supply the path to the configuration file"
    else:
        Watchers(sys.argv[1]).run()
