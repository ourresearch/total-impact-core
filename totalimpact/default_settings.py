##################################################################
# Total Impact default configuration settings
# ALL KEYS HAVE TO BE UPPERCASE TO BE STORED IN APP SETTINGS
#

USER_AGENT = "TotalImpact/0.3.0" # User-Agent string to use on HTTP requests
VERSION = "bruce" # TI version
PROXY = "" # used with  providers-test-proxy.py script in the extras directory
CACHE_ENABLED = True # Memcache server enabled

# List of desired providers and their configuration files
# Alias methods will be called in the order of this list
PROVIDERS = [
    # this is up here because it can produce dois
    ("pubmed", {}),  # 1 because rate limited

    # best biblio providers go here, in order with best first
    ("crossref", {}),
    ("dryad", {}),            
    ("github", {}),
    ("slideshare", {}),

    # if-need-be biblio providers go here, in order with best first
    ("mendeley", {}),
    ("bibtex", {}),
    ("dataone", {}),
    ("webpage", {}),

    # don't-have-biblio providers go here, alphabetical order
    ("citeulike", {}),   
    ("delicious", {}),   
    ("facebook", {}),   
    ("plosalm", {}),
    ("scienceseeker", {}),
    # ("researchblogging", {}), # takes too long
    # ("scopus", {}),
    ("topsy", {}),
    ("wikipedia", {}),
]

