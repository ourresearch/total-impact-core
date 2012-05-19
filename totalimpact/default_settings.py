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
        "class" : "totalimpact.providers.crossref.Crossref",
        "workers":10,
        "metrics": {}
    },
    "delicious":{
        "class" : "totalimpact.providers.delicious.Delicious",
        "workers":10,
        "metrics": {
            "watchers": {
                "static_meta" : {
                    "display_name": "bookmarks",
                    "provider": "Delicious",
                    "provider_url": "http://www.delicious.com/",
                    "description": "The number of bookmarks to this artifact (maximum=100).",
                    "icon": "http://www.delicious.com/favicon.ico",
                }
            }
        }
    },   
    "dryad": {
        "class" : "totalimpact.providers.dryad.Dryad",
        "workers":10,
        "metrics": {
            "package_views": {
                "static_meta" : {
                    "display_name": "package views",
                    "provider": "Dryad",
                    "provider_url": "http:\/\/www.datadryad.org\/",
                    "description": "Dryad package views: number of views of the main package page",
                    "icon": "http:\/\/datadryad.org\/favicon.ico",
                }
            },
            "total_downloads": {
                "static_meta":{
                    "display_name": "total downloads",
                    "provider": "Dryad",
                    "provider_url": "http:\/\/www.datadryad.org\/",
                    "description": "Dryad total downloads: combined number of downloads of the data package and data files",
                    "icon": "http:\/\/datadryad.org\/favicon.ico",
                }
            },
            "most_downloaded_file":{
                "static_meta":{
                    "display_name": "most downloaded file",
                    "provider": "Dryad",
                    "provider_url": "http:\/\/www.datadryad.org\/",
                    "description": "Dryad most downloaded file: number of downloads of the most commonly downloaded data package component",
                    "icon": "http:\/\/datadryad.org\/favicon.ico",
                }
            }
        }
    },            
    "github":{
        "class" : "totalimpact.providers.github.Github",
        "workers":10,
        "metrics": {
            "watchers": {
                "static_meta" : {
                    "display_name": "watchers",
                    "provider": "GitHub",
                    "provider_url": "http://github.com",
                    "description": "The number of people who are watching the GitHub repository",
                    "icon": "https://github.com/fluidicon.png",
                }
            },
            "forks": {
                "static_meta" : {
                    "display_name": "forks",
                    "provider": "GitHub",
                    "provider_url": "http://github.com",
                    "description": "The number of people who have forked the GitHub repository",
                    "icon": "https://github.com/fluidicon.png",
                }
            }
        }        
    },
    "mendeley":{
        "class" : "totalimpact.providers.mendeley.Mendeley",
        "workers":10,
        "metrics": {
            "readers": {
                "static_meta" : {
                    "display_name": "watchers",
                    "provider": "Mendeley",
                    "provider_url": "http://www.mendeley.com/",
                    "description": "The number of readers who have added the article to their libraries",
                    "icon": "http://www.mendeley.com/favicon.ico",
                }
            },    
            "groups": {
                "static_meta" : {
                    "display_name": "watchers",
                    "provider": "Mendeley",
                    "provider_url": "http://www.mendeley.com/",
                    "description": "The number of groups who have added the article to their libraries",
                    "icon": "http://www.mendeley.com/favicon.ico",
                }
            },  
        }
    },  
    "topsy":{
        "class" : "totalimpact.providers.topsy.Topsy",
        "workers":10,
        "metrics": {
            "tweets": {
                "static_meta" : {
                    "display_name": "tweets",
                    "provider": "Topsy",
                    "provider_url": "http://www.topsy.com/",
                    "description": "Tweets via Topsy, real-time search for the social web" + ", <a href='http://topsy.com'><img src='http://cdn.topsy.com/img/powered.png'/></a>", #part of otter terms of use to include this http://modules.topsy.com/app-terms/
                    "icon": "http://twitter.com/phoenix/favicon.ico" ,
                }
            },    
            "influential_tweets": {
                "static_meta" : {
                    "display_name": "influencial tweets",
                    "provider": "Topsy",
                    "provider_url": "http://www.topsy.com/",
                    "description": "Influential tweets via Topsy,Real-time search for the social web" + ", <a href='http://topsy.com'><img src='http://cdn.topsy.com/img/powered.png'/></a>", #part of otter terms of use to include this http://modules.topsy.com/app-terms/
                    "icon": "http://twitter.com/phoenix/favicon.ico" ,
                }
            }
        }
    },  
    "webpage":{
        "class" : "totalimpact.providers.webpage.Webpage",
        "workers":10,
        "metrics": {}
    },
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
                }
            }
        }
    },   

}

ALIASES = {
    "workers" : 10
}


# used by the class-loader to explore alternative paths from which to load
# classes depending on the context in which the configuration is used
#
MODULE_ROOT = "totalimpact"
