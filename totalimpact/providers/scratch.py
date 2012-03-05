import time 

class LonglivingManager(object):
    def run(self):
        threads = []
        config = self.get_config()
        providers = self.get_providers()
        for p in providers:
            threads.append(ProviderMetricsThread(p, config).run()) # start thread
        threads.append(ProviderAliasThread(providers).run())

class ProviderAliasThread(Thread):
    def __init__(self, providers):
        self.providers = providers
        self.config = None
        
    def run(self):
        while True:
            time.sleep(self.sleep_time())

class ProviderMetricsThread(Thread):

    def __init__(self, provider, config):
        self.provider = provider
        self.config = config

    def run(self):
        while True:
            # check queue
            # do stuff if item on queue
            metrics = self.provider.metrics(alias_object)
            time.sleep(self.provider.sleep_time())

class ProviderState(object):
    def sleep_time():
        return 1

class Provider(object):
    def member_items(self, query_string): raise NotImplementedError()
    def aliases(self, alias_object): raise NotImplementedError()
    def metrics(self, alias_object): raise NotImplementedError()
    
class Queue(object):
    def pop(self): raise NotImplementedError()
    
class CouchQueue(Queue):
    def pop(self):
        pass





class Collection(object):
    pass

class Item(object):
    pass

class Alias(object):
    pass
    
class Metrics(object):
    pass
    
class Biblio(object):
    pass