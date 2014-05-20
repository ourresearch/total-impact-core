#!/usr/bin/env python

import os, time, json, logging, Queue, copy, sys, datetime
from collections import defaultdict

from totalimpact import tiredis, default_settings, db
from totalimpact import item as item_module
from totalimpact.providers.provider import ProviderFactory, ProviderError
import tasks


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
        queue_length = self.myredis.llen(self.queue_name)       
        # logger.info(u">>>PUSHING to redis queue {queue_name}, current length {queue_length}".format(
        #     queue_name=self.name, queue_length=queue_length)) 
        self.myredis.lpush(self.queue_name, message_json)

    @classmethod
    def pop(cls, redis_queues, myredis):
        message = None
        logger.debug(u"about to pop from redis".format())

        (popped_queue_name, message_json) = myredis.brpop([queue.queue_name for queue in redis_queues]) 
        if message_json:
            queue_length = myredis.llen(popped_queue_name)                   
            logger.debug(u"{:20}: <<<POPPED from redis, current length {queue_length}, now to parse message".format(
                popped_queue_name, queue_length=queue_length))
            try:
                # logger.debug(u"{:20}: <<<POPPED from redis: starts {message_json}".format(
                #     self.name, message_json=message_json[0:50]))        
                message = json.loads(message_json) 
            except (TypeError, KeyError):
                logger.info(u"{:20}: ERROR processing redis message {message_json}".format(
                    popped_queue_name, message_json=message_json))
        return message



class Worker(object):
    def run_in_loop(self):
        while True:
            self.run()

    def spawn_and_loop(self):
        # t = threading.Thread(target=self.run_in_loop, name=self.name+"_thread")
        # t.daemon = True
        # t.start()    
        run_in_loop()




class Backend(Worker):
    def __init__(self, alias_queues, myredis):
        self.alias_queues = alias_queues
        self.myredis = myredis
        self.name = "Backend"


    def run(self):
        global thread_count
        res = None

        # go through alias_queues, with highest priority first
        alias_message = RedisQueue.pop([self.alias_queues["high"], self.alias_queues["low"]], self.myredis)

        if alias_message:
            tiid = alias_message["tiid"]
            aliases_dict = alias_message["aliases_dict"]
            res = tasks.refresh_tiid.delay(tiid, aliases_dict)

            # print res.ready()
            # print res.successful()
            # print res.get()
            # print res.result
            # print res.ready()
            # print res.successful()
        return res



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


    backend = Backend(alias_queues, myredis)
    try:
        backend.run_in_loop() # don't need to spawn this one
    except (KeyboardInterrupt, SystemExit): 
        # this approach is per http://stackoverflow.com/questions/2564137/python-how-to-terminate-a-thread-when-main-program-ends
        sys.exit()
 
if __name__ == "__main__":
    main()
