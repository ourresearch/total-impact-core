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
    # best biblio providers go here, in order with best first
    "crossref":{
        "workers":3
    },
    "dryad":{
        "workers":3
    },            
    "github":{
        "workers":3
    },
    "slideshare":{
        "workers":3
    },
    # if-need-be biblio providers go here
    "mendeley":{
        "workers":3
    },  
    "bibtex":{
        "workers":3
    },  
    "webpage":{
        "workers":3
    },
    # don't-have-biblio providers go here
    "plosalm":{
        "workers":3
    },  
    "delicious":{
        "workers":3
   },   
    "topsy":{
        "workers":3
    },  
    "wikipedia":{
        "workers":3
    },
}

ALIASES = {
}

