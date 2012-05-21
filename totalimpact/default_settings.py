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
    "crossref":{
        "workers":10
    },
    "delicious":{
        "workers":10
   },   
    "dryad": {
        "workers":10
    },            
    "github":{
        "workers":10   
    },
    "mendeley":{
        "workers":10
    },  
    "topsy":{
        "workers":10
    },  
    "webpage":{
        "workers":10
    },
    "wikipedia": {
        "workers": 10
    }
}

ALIASES = {
    "workers" : 10
}

