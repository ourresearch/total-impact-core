##################################################################
# Total Impact default configuration settings
# ALL KEYS HAVE TO BE UPPERCASE TO BE STORED IN APP SETTINGS
#

USER_AGENT = "TotalImpact/0.2.0" # User-Agent string to use on HTTP requests
VERSION = "jean-claude" # TI version
PROXY = "" # used with  providers-test-proxy.py script in the extras directory
CACHE_ENABLED = True # Memcache server enabled

# List of desired providers and their configuration files
# Alias methods will be called in the order of this list
PROVIDERS = [
    # this is up here because it can produce dois
    ("pubmed", { "workers":1 }),  # 1 because rate limited

    # best biblio providers go here, in order with best first
    ("crossref", { "workers":3 }),
    ("dryad", { "workers":3 }),            
    ("github", { "workers":3 }),
    ("slideshare", { "workers":3 }),

    # if-need-be biblio providers go here, in order with best first
    ("mendeley", { "workers":3 }),
    ("bibtex", { "workers":3 }),
    ("dataone", {  "workers":3 }),
    ("webpage", {  "workers":3 }),

    # don't-have-biblio providers go here, alphabetical order
    ("citeulike", { "workers":3 }),   
    ("delicious", { "workers":3 }),   
    ("facebook", { "workers":3 }),   
    ("plosalm", { "workers":3 }),
    # ("researchblogging", { "workers":3 }), # takes too long for interactive test
    ("topsy", { "workers":3 }),
    ("wikipedia", { "workers":3 }),
]

