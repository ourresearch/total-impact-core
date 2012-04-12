## ALL KEYS HAVE TO BE UPPERCASE TO BE STORED IN APP SETTINGS

SECRET_KEY = 'default-key'
BASE_DIR = "/Users/richard/Code/External/total-impact/"

# During HTTP requests, the User-Agent string to use
USER_AGENT = "TotalImpact/0.2.0"
# TI version
VERSION = "jean-claude"

# Database information
DB_NAME = 'ti'
DB_URL = "http://localhost:5984/"
DB_VIEWS = {
    "_id": "_design/queues",
    "language": "javascript",
    "views": {
        "metrics": {},
        "aliases": {}
    	} 
    }

    

# List of desired providers and their configuration files
# Alias methods will be called in the order of this list
#
PROVIDERS = [
    {
        "class" : "totalimpact.providers.wikipedia.Wikipedia",
        "config" : "totalimpact/providers/wikipedia.conf.json"
    },
    {
        "class" : "totalimpact.providers.dryad.Dryad",
        "config" : "totalimpact/providers/dryad.conf.json"
    },
    {
        "class" : "totalimpact.providers.github.Github",
        "config" : "totalimpact/providers/github.conf.json"
    }
]

# used by the class-loader to explore alternative paths from which to load
# classes depending on the context in which the configuration is used
#
MODULE_ROOT = "totalimpact"
