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
CACHE_ENABLED = "1"

# List of desired providers and their configuration files
# Alias methods will be called in the order of this list
#
PROVIDERS = {
    "wikipedia":{
        "class" : "totalimpact.providers.wikipedia.Wikipedia",
        "config" : "totalimpact/providers/wikipedia.conf.json"
    },
    "dryad": {
        "class" : "totalimpact.providers.dryad.Dryad",
        "config" : "totalimpact/providers/dryad.conf.json"
    },
    "github": {
        "class" : "totalimpact.providers.github.Github",
        "config" : "totalimpact/providers/github.conf.json"
    }
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
