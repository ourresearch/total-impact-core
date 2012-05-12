##################################################################
#
# Total Impact default configuration settings
#
# If you want to change these settings for your own deployment, 
# create a file entitled app.cfg using this file as a template. 
# Any settings you define in app.cfg will override the default 
# settings contained in this file.
#
# If you want to use a different path or filename than app.cfg
# then set the TOTALIMPACT_CONFIG environment variable to the
# path to your config file
#
# ALL KEYS HAVE TO BE UPPERCASE TO BE STORED IN APP SETTINGS
#

# During HTTP requests, the User-Agent string to use
USER_AGENT = "TotalImpact/0.2.0"
# TI version
VERSION = "jean-claude"

# Database information
# Default config is to connect to couchdb on localhost with no login 
# credentials. 
DB_NAME = 'ti'    
DB_URL = "http://localhost:5984/"
DB_USERNAME = ""
DB_PASSWORD = ""

# This is particularly useful when using the providers-test-proxy.py
# script in the extras directory
PROXY = ""

# Memcache server enabled
CACHE_ENABLED = True

# List of desired providers and their configuration files
# Alias methods will be called in the order of this list
#
PROVIDERS = {
    "wikipedia": {
        "class" : "totalimpact.providers.wikipedia.Wikipedia",
        "config" : "totalimpact/providers/wikipedia.conf.json",
        "timeout": 5,
	"workers": 10,
        "metrics": {
            "mentions": {
                "static_meta" : {
                    "display_name": "mentions",
                    "provider": "Wikipedia",
                    "provider_url": "http://www.wikipedia.org/",
                    "description": "Wikipedia is the free encyclopedia that anyone can edit.",
                    "icon": "http://wikipedia.org/favicon.ico",
                    "category": "NA",
                    "can_use_commercially": "NA",
                    "can_embed": "NA",
                    "can_aggregate": "NA",
                    "other_terms_of_use": "NA"
                }
            }
        }
    },
    "dryad": {
        "class" : "totalimpact.providers.dryad.Dryad",
        "config" : "totalimpact/providers/dryad.conf.json",
        "supported_namespaces" : ["doi"],
        "timeout" : 5,
	"workers":10,
        "metrics": {
            "package_views": {
                "static_meta" : {
                    "display_name": "package views",
                    "provider": "Dryad",
                    "provider_url": "http:\/\/www.datadryad.org\/",
                    "description": "Dryad package views: number of views of the main package page",
                    "icon": "http:\/\/datadryad.org\/favicon.ico",
                    "category": "views",
                    "can_use_commercially": "1",
                    "can_embed": "1",
                    "can_aggregate": "1",
                    "other_terms_of_use": "CC0"
                }
            },
            "total_downloads": {
                "static_meta":{
                    "display_name": "total downloads",
                    "provider": "Dryad",
                    "provider_url": "http:\/\/www.datadryad.org\/",
                    "description": "Dryad total downloads: combined number of downloads of the data package and data files",
                    "icon": "http:\/\/datadryad.org\/favicon.ico",
                    "category": "downloads",
                    "can_use_commercially": "1",
                    "can_embed": "1",
                    "can_aggregate": "1",
                    "other_terms_of_use": "CC0"
                }
            },
            "most_downloaded_file":{
                "static_meta":{
                    "display_name": "most downloaded file",
                    "provider": "Dryad",
                    "provider_url": "http:\/\/www.datadryad.org\/",
                    "description": "Dryad most downloaded file: number of downloads of the most commonly downloaded data package component",
                    "icon": "http:\/\/datadryad.org\/favicon.ico",
                    "category": "downloads",
                    "can_use_commercially": "1",
                    "can_embed": "1",
                    "can_aggregate": "1",
                    "other_terms_of_use": "CC0"
                }
            }
        }
    },
    "github":{
        "class" : "totalimpact.providers.github.Github",
        "config" : "totalimpact/providers/github.conf.json",
        "supported_namespaces" : ["github"],
	"workers":10,
        "metrics": {}
    }
}

ALIASES = {
    "workers" : 10
}

#TODO this should be created from the providers config item.
METRIC_NAMES = [
    "wikipedia:mentions",
    "dryad:package_views",
    "dryad:total_downloads",
    "dryad:most_downloaded_file",
    "github:watchers",
    "github:forks",
]

# used by the class-loader to explore alternative paths from which to load
# classes depending on the context in which the configuration is used
#
MODULE_ROOT = "totalimpact"
