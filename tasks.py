import logging
import celery
import os
import json

from totalimpact import item as item_module
from totalimpact import db
from totalimpact import tiredis
from totalimpact.providers.provider import ProviderFactory, ProviderError

logger = logging.getLogger("core.tasks")

celery_app = celery.Celery('tasks', 
    broker=os.getenv("CLOUDAMQP_URL", "amqp://guest@localhost//")
    )

myredis = tiredis.from_url(os.getenv("REDISTOGO_URL"))


class TaskAlertIfFail(celery.Task):
    def __call__(self, *args, **kwargs):
        """In celery task this function call the run method, here you can
        set some environment variable before the run of the task"""
        # logger.info(u"Starting to run")
        return self.run(*args, **kwargs)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        url_slug="unknown"
        # for arg in args:
        #     if isinstance(arg, User):
        #         url_slug = arg.url_slug
        logger.error(u"Celery task failed on {task_name}, task_id={task_id}".format(
            task_name=self.name, task_id=task_id))


def provider_method_wrapper(tiid, input_aliases_dict, provider, method_name, analytics_credentials, myredis, aliases_providers_run, callback):

    logger.info(u"{:20}: in provider_method_wrapper with {tiid} {provider_name} {method_name} with {aliases}".format(
       "wrapper", tiid=tiid, provider_name=provider.provider_name, method_name=method_name, aliases=input_aliases_dict))

    provider_name = provider.provider_name
    worker_name = provider_name+"_worker"

    input_alias_tuples = item_module.alias_tuples_from_dict(input_aliases_dict)
    method = getattr(provider, method_name)

    try:
        if provider.uses_analytics_credentials(method_name):
            method_response = method(input_alias_tuples, analytics_credentials=analytics_credentials)
        else:
            method_response = method(input_alias_tuples)
    except ProviderError:
        method_response = None
        logger.info(u"{:20}: **ProviderError {tiid} {method_name} {provider_name} ".format(
            worker_name, tiid=tiid, provider_name=provider_name.upper(), method_name=method_name.upper()))

    if method_name == "aliases":
        # update aliases to include the old ones too
        aliases_providers_run += [provider_name]
        if method_response:
            new_aliases_dict = item_module.alias_dict_from_tuples(method_response)
            new_canonical_aliases_dict = item_module.canonical_aliases(new_aliases_dict)
            response = item_module.merge_alias_dicts(new_canonical_aliases_dict, input_aliases_dict)
        else:
            response = input_aliases_dict
    else:
        response = method_response

    logger.info(u"{:20}: /biblio_print, RETURNED {tiid} {method_name} {provider_name} : {response}".format(
        worker_name, tiid=tiid, method_name=method_name.upper(), 
        provider_name=provider_name.upper(), response=response))


    callback(tiid, response, method_name, analytics_credentials, myredis, provider_name, aliases_providers_run)


    return response




# last variable is an artifact so it has same call signature as other callbacks
def add_to_database_if_nonzero( 
        tiid, 
        new_content, 
        method_name, 
        analytics_credentials, 
        myredis,
        provider_name,
        dummy_already_run=None):

    try:
        if new_content:
            # don't need item with metrics for this purpose, so don't bother getting metrics from db
            print tiid, new_content

            item_obj = item_module.Item.query.get(tiid)

            if item_obj:
                if method_name=="aliases":
                    item_obj = item_module.add_aliases_to_item_object(new_content, item_obj)
                elif method_name=="biblio":
                    updated_item_doc = item_module.update_item_with_new_biblio(new_content, item_obj, provider_name)
                elif method_name=="metrics":
                    for metric_name in new_content:
                        item_obj = item_module.add_metric_to_item_object(metric_name, new_content[metric_name], item_obj)
                else:
                    logger.warning(u"ack, supposed to save something i don't know about: " + str(new_content))
    finally:
        db.session.remove()

    # do this no matter what, but as last thing
    if method_name=="metrics":
        myredis.set_provider_finished(tiid, provider_name)

    return



def add_to_alias_queue_and_database( 
            tiid, 
            aliases_dict, 
            method_name, 
            analytics_credentials, 
            myredis,
            provider_name,
            alias_providers_already_run):

    add_to_database_if_nonzero(tiid, aliases_dict, method_name, analytics_credentials, myredis, provider_name, alias_providers_already_run)

    alias_message = {
            "tiid": tiid, 
            "aliases_dict": aliases_dict,
            "analytics_credentials": analytics_credentials,
            "alias_providers_already_run": alias_providers_already_run
        }        

    def push_to_alias_queue(priority, message):
        message_json = json.dumps(message)
        myredis.lpush("aliasqueue_"+priority, message_json)

    # always push to highest priority queue if we're already going
    push_to_alias_queue("high", alias_message)




@celery_app.task(base=TaskAlertIfFail)
def provider_run(provider_message, provider_name):

    global myredis

    provider = ProviderFactory.get_provider(provider_name)

    logger.info(u"POPPED from queue for {provider}".format(
       provider=provider.provider_name))
    tiid = provider_message["tiid"]
    aliases_dict = provider_message["aliases_dict"]
    method_name = provider_message["method_name"]
    analytics_credentials = provider_message["analytics_credentials"]
    alias_providers_already_run = provider_message["alias_providers_already_run"]

    if (method_name == "metrics") and provider.provides_metrics:
        myredis.set_provider_started(tiid, provider.provider_name)

    if method_name == "aliases":
        callback = add_to_alias_queue_and_database
    else:
        callback = add_to_database_if_nonzero

    provider_method_wrapper(tiid, aliases_dict, provider, method_name, analytics_credentials, myredis, alias_providers_already_run, callback)





