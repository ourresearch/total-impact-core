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
        "supported_namespaces" : ["doi"],
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
        "supported_namespaces" : ["github"],
	    "workers":10,
        "metrics": {
            "watchers": {
                "static_meta" : {
                    "display_name": "watchers",
                    "provider": "GitHub",
                    "provider_url": "http://github.com",
                    "description": "The number of people who are watching the GitHub repository",
                    "icon": "https://github.com/fluidicon.png",
                    "category": "views",
                    "can_use_commercially": "",
                    "can_embed": "",
                    "can_aggregate": "",
                    "other_terms_of_use": ""
                }
            },
            "forks": {
                "static_meta" : {
                    "display_name": "forks",
                    "provider": "GitHub",
                    "provider_url": "http://github.com",
                    "description": "The number of people who have forked the GitHub repository",
                    "icon": "https://github.com/fluidicon.png",
                    "category": "reuse",
                    "can_use_commercially": "",
                    "can_embed": "",
                    "can_aggregate": "",
                    "other_terms_of_use": ""
                }
            }
        }        
    }
}

ALIASES = {
    "workers" : 10
}


# used by the class-loader to explore alternative paths from which to load
# classes depending on the context in which the configuration is used
#
MODULE_ROOT = "totalimpact"
