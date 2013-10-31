##################################################################
# Total Impact default configuration settings
# ALL KEYS HAVE TO BE UPPERCASE TO BE STORED IN APP SETTINGS
#

USER_AGENT = "ImpactStory/0.4.0" # User-Agent string to use on HTTP requests
VERSION = "cristhian" # version
PROXY = "" # used with  providers-test-proxy.py script in the extras directory
CACHE_ENABLED = True # Memcache server enabled

# List of desired providers and their configuration files
# Alias methods will be called in the order of this list
PROVIDERS = [
    # this is up here because it can produce dois
    ("pubmed", {}),

    # best biblio providers go here, in order with best first
    ("crossref", {}),
    ("dryad", {}),            
    ("figshare", {}),            
    ("github", {}),
    ("slideshare", {}),
    ("youtube", {}),

    # if-need-be biblio providers go here, in order with best first
    ("mendeley", {}),
    ("bibtex", {}),
    ("dataone", {}),
    ("webpage", {}),

    # don't-have-biblio providers go here, alphabetical order
    ("citeulike", {}),   
    ("delicious", {}),   
    ("plosalm", {}),
    ("plossearch", {}),
    ("pmc", {}),
    ("scienceseeker", {}),
    ("scopus", {}),
    ("topsy", {}),
    ("wikipedia", {}),
]

