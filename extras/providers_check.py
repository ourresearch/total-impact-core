#!/usr/bin/env python
#
# Providers Check
#
# This is currently a very basic check for providers
#

from totalimpact.dao import Dao
from totalimpact.models import Item, ItemFactory, Aliases

from totalimpact.providers.github import Github
from totalimpact.providers.wikipedia import Wikipedia
from totalimpact.providers.dryad import Dryad

import sys
import test
import time

from pprint import pprint

from totalimpact.providers.github import Github
from totalimpact.providers.wikipedia import Wikipedia
from totalimpact.api import app

import logging

from optparse import OptionParser


class ProvidersCheck:

    def __init__(self):
        self.mydao = Dao(app.config["DB_NAME"], app.config["DB_URL"], app.config["DB_USERNAME"], app.config["DB_PASSWORD"])

    # Aux methods which record failures in appropriate member variables 
    # so they can be reported and acted upon

    def check_aliases(self, name, result, expected):
        if expected not in result:
            self.errors['aliases'].append("Aliases error for %s - Result '%s' does not match expected value '%s'" % (
                name, result, expected ))

    def check_metric(self, name, result, expected):
        if result != expected:
            self.errors['metrics'].append("Metric error for %s - Result '%s' does not match expected value '%s'" % (
                name, result, expected ))

    def check_members(self, name, result, expected):
        if result != expected:
            self.errors['members'].append("Members error for %s - Result '%s' does not match expected value '%s'" % (
                name, result, expected ))

    def checkDryad(self):
        # Test reading data from Dryad
        item = ItemFactory.make(self.mydao, app.config["PROVIDERS"])
        item.aliases.add_alias('doi', '10.5061/dryad.7898')
        item_aliases_list = item.aliases.get_aliases_list()

        dryad = Dryad()
        new_aliases = dryad.aliases(item_aliases_list)
        new_metrics = dryad.metrics(item_aliases_list)

        self.check_aliases('dryad.url', new_aliases, ("url", 'http://hdl.handle.net/10255/dryad.7898'))
        self.check_aliases('dryad.doi', new_aliases, ("doi", '10.5061/dryad.7898'))
        self.check_aliases('dryad.title', new_aliases, ("title", 'data from: can clone size serve as a proxy for clone age? an exploration using microsatellite divergence in populus tremuloides'))
    
    def checkWikipedia(self):
        # Test reading data from Wikipedia
        item = ItemFactory.make(self.mydao, app.config["PROVIDERS"])
        item.aliases.add_alias("doi", "10.1371/journal.pcbi.1000361")
        item.aliases.add_alias("url", "http://cottagelabs.com")
        item_aliases_list = item.aliases.get_aliases_list()

        wikipedia = Wikipedia()
        # No aliases for wikipedia
        #new_aliases = wikipedia.aliases(item_aliases_list)
        new_metrics = wikipedia.metrics(item_aliases_list)

        self.check_metric('wikipedia:mentions', new_metrics['wikipedia:mentions'], 1)

    def checkGithub(self):
        item = ItemFactory.make(self.mydao, app.config["PROVIDERS"])

        github = Github()
        members = github.member_items("egonw", "github_user")
        self.check_members('github.github_user', members, 
            [('github', ('egonw', 'blueobelisk.debian')),
             ('github', ('egonw', 'ron')),
             ('github', ('egonw', 'pubchem-cdk')),
             ('github', ('egonw', 'org.openscience.cdk')),
             ('github', ('egonw', 'java-rdfa')),
             ('github', ('egonw', 'cdk')),
             ('github', ('egonw', 'RobotDF')),
             ('github', ('egonw', 'egonw.github.com')),
             ('github', ('egonw', 'knime-chemspider')),
             ('github', ('egonw', 'gtd')),
             ('github', ('egonw', 'cheminfbenchmark')),
             ('github', ('egonw', 'cdk-taverna')),
             ('github', ('egonw', 'groovy-jcp')),
             ('github', ('egonw', 'jnchem')),
             ('github', ('egonw', 'acsrdf2010')),
             ('github', ('egonw', 'Science-3.0')),
             ('github', ('egonw', 'SNORQL')),
             ('github', ('egonw', 'ctr-cdk-groovy')),
             ('github', ('egonw', 'CDKitty')),
             ('github', ('egonw', 'rednael')),
             ('github', ('egonw', 'de.ipbhalle.msbi')),
             ('github', ('egonw', 'collaborative.cheminformatics')),
             ('github', ('egonw', 'xws-taverna')),
             ('github', ('egonw', 'cheminformatics.classics')),
             ('github', ('egonw', 'chembl.rdf')),
             ('github', ('egonw', 'blueobelisk.userscript')),
             ('github', ('egonw', 'ojdcheck')),
             ('github', ('egonw', 'nmrshiftdb-rdf')),
             ('github', ('egonw', 'bioclipse.ons')),
             ('github', ('egonw', 'medea_bmc_article'))])

        item.aliases.add_alias("github", "egonw/gtd")
        item_aliases_list = item.aliases.get_aliases_list()

        new_metrics = github.metrics(item_aliases_list)

        self.check_metric('github:forks', new_metrics['github:forks'], 0)
        self.check_metric('github:watchers', new_metrics['github:watchers'], 7)

    def checkAll(self):
        # This will get appended to by each check if it finds any data mismatches
        self.errors = {'aliases':[], 'metrics':[], 'members':[]}
        print "Checking Dryad provider"
        self.checkDryad()
        print "Checking Wikipedia provider"
        self.checkWikipedia()
        print "Checking Github provider"
        self.checkGithub()
    
        if sum([len(self.errors[key]) for key in ['aliases','metrics','members']]) > 0:
            print "Checks complete, the following data inconsistencies were found"
            for key in self.errors.keys():
                print "\n== %s ===============================" % key
                for error in self.errors[key]:
                    print error
        else:
            print "Checks complete, no data inconsistencies were found"
       


if __name__ == '__main__':

    parser = OptionParser()
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose", default=False,
                      help="print debugging output")

    (options, args) = parser.parse_args()
    
    if not options.verbose:
        logger = logging.getLogger('')
        logger.setLevel(logging.WARNING)

    check = ProvidersCheck()    
    check.checkAll()


