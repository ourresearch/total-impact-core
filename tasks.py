import time 
import os
import json
import logging
import celery
from celery.decorators import task
from celery.signals import task_postrun, task_prerun, task_failure
from celery import group, chain, chord
from celery import Celery


from totalimpact import item as item_module
from totalimpact import db
from totalimpact import tiredis, default_settings
from totalimpact.providers.provider import ProviderFactory, ProviderError

logger = logging.getLogger("core.tasks")
myredis = tiredis.from_url(os.getenv("REDIS_URL"))

celery_app = Celery()
celery_app.config_from_object('celeryconfig')

@task_prerun.connect()
def task_starting_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):    
    try:
        if "chain_dummy" in task.name:
            logging.info(">>>STARTED: {task}".format(
                task_id=task_id, task=task, args=args, kwargs=kwargs))
        else:
            logging.info(">>>STARTED: {task} {args}".format(
                task_id=task_id, task=task, args=args, kwargs=kwargs))
    except KeyError:
        pass

@task_postrun.connect()
def task_finished_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    try:    
        if "chain_dummy" in task.name:
            logging.info("<<<FINISHED: {task}".format(
                task_id=task_id, task=task, args=args, kwargs=kwargs, retval=retval, state=state))
        else:
            logging.info("<<<FINISHED: {task} {args}".format(
                task_id=task_id, task=task, args=args, kwargs=kwargs, retval=retval, state=state))
    except KeyError:
        pass

@task_failure.connect
def task_failure_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    try:
        logger.error(u"Celery task FAILED on task_id={task_id}, {args}".format(
            task_id=task_id, args=args))
    except KeyError:
        pass




def provider_method_wrapper(tiid, input_aliases_dict, provider, method_name, myredis):

    logger.info(u"{:20}: in provider_method_wrapper with {tiid} {provider_name} {method_name} with {aliases}".format(
       "wrapper", tiid=tiid, provider_name=provider.provider_name, method_name=method_name, aliases=input_aliases_dict))

    provider_name = provider.provider_name
    worker_name = provider_name+"_worker"

    if isinstance(input_aliases_dict, list):
        input_aliases_dict = item_module.alias_dict_from_tuples(input_aliases_dict)    

    input_alias_tuples = item_module.alias_tuples_from_dict(input_aliases_dict)
    method = getattr(provider, method_name)

    try:
        method_response = method(input_alias_tuples)
    except ProviderError:
        method_response = None
        logger.info(u"{:20}: **ProviderError {tiid} {method_name} {provider_name} ".format(
            worker_name, tiid=tiid, provider_name=provider_name.upper(), method_name=method_name.upper()))

    logger.info(u"{:20}: /biblio_print, RETURNED {tiid} {method_name} {provider_name} : {method_response}".format(
        worker_name, tiid=tiid, method_name=method_name.upper(), 
        provider_name=provider_name.upper(), method_response=method_response))

    if method_name == "aliases" and method_response:
        initial_alias_dict = item_module.alias_dict_from_tuples(method_response)
        new_canonical_aliases_dict = item_module.canonical_aliases(initial_alias_dict)
        full_aliases_dict = item_module.merge_alias_dicts(new_canonical_aliases_dict, input_aliases_dict)
    else:
        full_aliases_dict = input_aliases_dict

    add_to_database_if_nonzero(tiid, method_response, method_name, myredis, provider_name)

    return full_aliases_dict




# last variable is an artifact so it has same call signature as other callbacks
def add_to_database_if_nonzero( 
        tiid, 
        new_content, 
        method_name, 
        myredis,
        provider_name):
    try:
        if new_content:
            # don't need item with metrics for this purpose, so don't bother getting metrics from db
            item_obj = item_module.Item.query.get(tiid)

            if item_obj:
                if method_name=="aliases":
                    if isinstance(new_content, list):
                        new_content = item_module.alias_dict_from_tuples(new_content)    
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


# @task
# def chordfinisher(group_result, **kwargs):
#     return group_result[0]

@task
def chain_dummy(first_arg, **kwargs):
    # print "sleeping"
    # time.sleep(3)
    try:
        return first_arg[0]
    except KeyError:
        return first_arg


@task
def provider_run(aliases_dict, tiid, method_name, provider_name):

    global myredis

    provider = ProviderFactory.get_provider(provider_name)

    logger.info(u"in provider_run for {provider}".format(
       provider=provider.provider_name))

    if (method_name == "metrics") and provider.provides_metrics:
        myredis.set_provider_started(tiid, provider.provider_name)

    response = provider_method_wrapper(tiid, aliases_dict, provider, method_name, myredis)

    return response



def sniffer(item_aliases, provider_config=default_settings.PROVIDERS):

    (genre, host) = item_module.decide_genre(item_aliases)

    all_metrics_providers = [provider.provider_name for provider in 
                    ProviderFactory.get_providers(provider_config, "metrics")]

    if (genre == "article") and (host != "arxiv"):
        run = [[("aliases", provider)] for provider in ["mendeley", "crossref", "pubmed", "altmetric_com"]]
        run += [[("biblio", provider) for provider in ["crossref", "pubmed", "mendeley", "webpage"]]]
        run += [[("metrics", provider) for provider in all_metrics_providers]]
    elif (host == "arxiv") or ("doi" in item_aliases):
        run = [[("aliases", provider)] for provider in [host, "altmetric_com"]]
        run += [[("biblio", provider) for provider in [host, "mendeley"]]]
        run += [[("metrics", provider) for provider in all_metrics_providers]]
    else:
        # relevant alias and biblio providers are always the same
        relevant_providers = [host]
        if relevant_providers == ["unknown"]:
            relevant_providers = ["webpage"]
        run = [[("aliases", provider)] for provider in relevant_providers]
        run += [[("biblio", provider) for provider in relevant_providers]]
        run += [[("metrics", provider) for provider in all_metrics_providers]]

    return(run)


@task
def refresh_tiid(tiid, aliases_dict):

    pipeline = sniffer(aliases_dict)
    chain_list = []
    for step_config in pipeline:
        group_list = []
        for (method_name, provider_name) in step_config:
            if not chain_list:
                # pass the alias dict in to the first one in the whole chain
                group_list.append(provider_run.si(aliases_dict, tiid, method_name, provider_name))
                # group_list.append(provider_run.si(aliases_dict, tiid, method_name, provider_name).set(queue=provider_name))
            else:
                group_list.append(provider_run.s(tiid, method_name, provider_name))
                # group_list.append(provider_run.s(tiid, method_name, provider_name).set(queue=provider_name))
        if group_list:
            chain_list.append(group(group_list))
            chain_list.append(chain_dummy.s(dummy="DUMMY_{method_name}_{provider_name}".format(
                method_name=method_name, provider_name=provider_name)))

    workflow = chain(chain_list)

    app.control.time_limit('tasks.crawl_the_web',
                               soft=60, hard=120, reply=True)

    res = workflow.delay()
    return tiid


def put_on_celery_queue(tiid, aliases_dict):
    logger.info(u"put_on_celery_queue {tiid}".format(
        tiid=tiid))

    res = refresh_tiid.delay(tiid, aliases_dict)

    print res
    print res.ready()
    print res.successful()
    print res.get()
    print res.result
    print res.ready()
    print res.successful()
    return res    
