#!/usr/bin/env python

from flask import Flask, jsonify, json, request, redirect, abort, make_response
from flask import render_template, flash
import os, json, time

from totalimpact import dao
from totalimpact.models import Item, Collection, ItemFactory, CollectionFactory
from totalimpact.providers.provider import ProviderFactory, ProviderConfigurationError
from totalimpact.tilogging import logging
from totalimpact import default_settings


# set up logging
logger = logging.getLogger(__name__)

from totalimpact.api import app

if __name__ == "__main__":

    logger = logging.getLogger()

    mydao = dao.Dao(
        app.config["DB_NAME"],
        app.config["DB_URL"],
        app.config["DB_USERNAME"],
        app.config["DB_PASSWORD"]
    ) 

    # Adding this by handle. fileConfig doesn't allow filters to be added
    from totalimpact.backend import ctxfilter
    handler = logging.handlers.RotatingFileHandler("logs/total-impact.log")
    handler.level = logging.DEBUG
    formatter = logging.Formatter("%(asctime)s %(levelname)8s %(item)8s %(thread)s%(provider)s - %(message)s")#,"%H:%M:%S,%f")
    handler.formatter = formatter
    handler.addFilter(ctxfilter)
    logger.addHandler(handler)
    ctxfilter.threadInit()

    logger.debug("test")

    from totalimpact.backend import TotalImpactBackend, ProviderMetricsThread, ProvidersAliasThread, StoppableThread, QueueConsumer
    from totalimpact.providers.provider import Provider, ProviderFactory

    # Start all of the backend processes
    print "Starting alias retrieval thread"
    providers = ProviderFactory.get_providers(app.config["PROVIDERS"])

    alias_threads = []
    thread_count = app.config["ALIASES"]["workers"]
    for idx in range(thread_count):
        at = ProvidersAliasThread(providers, mydao, idx)
        at.thread_id = 'AliasThread(%i)' % idx
        at.start()
        alias_threads.append(at)

    print "Starting metric retrieval threads..."
    # Start each of the metric providers
    metrics_threads = []
    for provider in providers:
        providers = ProviderFactory.get_providers(app.config["PROVIDERS"])
        thread_count = app.config["PROVIDERS"][provider.name]["workers"]
        print "  ", provider.provider_name
        for idx in range(thread_count):
            thread = ProviderMetricsThread(provider, mydao)
            metrics_threads.append(thread)
            thread.thread_id = thread.thread_id + '(%i)' % idx
            thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt, e:
        pass

    from totalimpact.queue import alias_queue_seen
    from totalimpact.queue import metric_queue_seen

    print "Stopping alias threads"
    for at in alias_threads:
        at.stop()
    print "Stopping metric threads"
    for thread in metrics_threads:
        thread.stop()
    print "Waiting on metric threads"
    for thread in metrics_threads:
        thread.join()
    print "Waiting on alias thread"
    for at in alias_threads:
        at.join()
    print "All stopped"


