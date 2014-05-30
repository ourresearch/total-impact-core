import time 
import os
import json
import logging
import datetime
import celery
from celery.decorators import task
from celery.signals import task_postrun, task_prerun, task_failure, worker_process_init
from celery import group, chain, chord
# from celery.app import default_app as celery_app
from eventlet import timeout

from totalimpact import item as item_module
from totalimpact import db
from totalimpact import tiredis, default_settings
from totalimpact.providers.provider import ProviderFactory, ProviderError, ProviderTimeout

logger = logging.getLogger("core.tasks")
myredis = tiredis.from_url(os.getenv("REDIS_URL"))




class SqlAlchemyTask(celery.Task):
    """An abstract Celery Task that ensures that the connection the the
    database is closed on task completion"""
    abstract = True

    # def after_return(self, status, retval, task_id, args, kwargs, einfo):
    #     db.session.remove()



@task_postrun.connect()
def task_postrun_handler(*args, **kwargs):    
    db.session.remove()


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, args=None, kwargs=None, exception=None, traceback=None, einfo=None, **kwds):
    try:
        logger.error(u"Celery task FAILED on task_id={task_id}, {exception}, {traceback}, {einfo}, {args}".format(
            task_id=task_id, args=args, exception=exception, einfo=einfo))
    except KeyError:
        pass




def provider_method_wrapper(tiid, input_aliases_dict, provider, method_name):

    # logger.info(u"{:20}: in provider_method_wrapper with {tiid} {provider_name} {method_name} with {aliases}".format(
    #    "wrapper", tiid=tiid, provider_name=provider.provider_name, method_name=method_name, aliases=input_aliases_dict))

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

    add_to_database_if_nonzero(tiid, method_response, method_name, provider_name)

    return full_aliases_dict




# last variable is an artifact so it has same call signature as other callbacks
def add_to_database_if_nonzero( 
        tiid, 
        new_content, 
        method_name, 
        provider_name):

    if new_content:
        # don't need item with metrics for this purpose, so don't bother getting metrics from db

        try:
            item_obj = item_module.Item.query.get(tiid)
        except:
            db.session.remove()
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

    return


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



@task(base=SqlAlchemyTask, time_limit=10)
def chain_dummy(first_arg, **kwargs):
    try:
        response = first_arg[0]
    except KeyError:
        response = first_arg

    return response

def get_ratelimit_token(provider_name):
    return (1, None)

@task(base=SqlAlchemyTask)
def provider_run(aliases_dict, tiid, method_name, provider_name):

    timeout_seconds = 40
    try:
        with timeout.Timeout(timeout_seconds):
            provider = ProviderFactory.get_provider(provider_name)

            # logger.info(u"in provider_run for {provider}".format(
            #    provider=provider.provider_name))

            (token, estimated_time) = get_ratelimit_token(provider_name)
            if not token:
                 provider_run.retry(args=[aliases_dict, tiid, method_name, provider_name],
                        countdown=estimated_time)

            response = provider_method_wrapper(tiid, aliases_dict, provider, method_name)

    except timeout.Timeout:
        msg = u"TIMEOUT in provider_run for {provider} {method_name} {tiid} after {timeout_seconds} seconds".format(
           provider=provider.provider_name, method_name=method_name, tiid=tiid, timeout_seconds=timeout_seconds)
        # logger.warning(msg)  # message is written elsewhere
        raise ProviderTimeout(msg)

    return response





@task(base=SqlAlchemyTask, time_limit=60)
def refresh_tiid(tiid, aliases_dict):
    pipeline = sniffer(aliases_dict)
    chain_list = []
    for step_config in pipeline:
        group_list = []
        for (method_name, provider_name) in step_config:
            if not chain_list:
                # pass the alias dict in to the first one in the whole chain
                group_list.append(provider_run.si(aliases_dict, tiid, method_name, provider_name).set())
                # group_list.append(provider_run.si(aliases_dict, tiid, method_name, provider_name).set(queue="provider."+provider_name))
            else:
                group_list.append(provider_run.s(tiid, method_name, provider_name).set())
                # group_list.append(provider_run.s(tiid, method_name, provider_name).set(queue="provider."+"provider_name"))
        if group_list:
            chain_list.append(group(group_list))
            chain_list.append(chain_dummy.s(dummy="DUMMY_{method_name}_{provider_name}".format(
                method_name=method_name, provider_name=provider_name)))

    workflow = chain(chain_list)

    # see http://stackoverflow.com/questions/18872854/getting-task-id-inside-a-celery-task
    # workflow_tasks_task.task_id, 
    logger.info(u"before apply_async for tiid {tiid}, refresh_tiids id {task_id}".format(
        tiid=tiid, task_id=refresh_tiid.request.id))

    workflow_tasks_task = workflow.apply_async()

    # see http://stackoverflow.com/questions/18872854/getting-task-id-inside-a-celery-task
    # workflow_tasks_task.task_id, 
    logger.info(u"setting task id for tiid {tiid}, refresh_tiids id {task_id}, workflow_id {workflow_id}".format(
        tiid=tiid, task_id=refresh_tiid.request.id, workflow_id=workflow_tasks_task.task_id))
    myredis.set_task_id(tiid, workflow_tasks_task.task_id)

    return workflow_tasks_task


def put_on_celery_queue(tiid, aliases_dict, priority="high"):
    logger.info(u"put_on_celery_queue {tiid}".format(
        tiid=tiid))

    #see http://stackoverflow.com/questions/15239880/task-priority-in-celery-with-redis
    if "priority"=="high":
        priority = 0
    else:
        priority = 9

    refresh_tiid_task = refresh_tiid.apply_async(args=(tiid, aliases_dict), priority=priority)

    return refresh_tiid_task


