##################################################################
# Total Impact default configuration settings
# ALL KEYS HAVE TO BE UPPERCASE TO BE STORED IN APP SETTINGS
#

USER_AGENT = "ImpactStory/0.4.0" # User-Agent string to use on HTTP requests
VERSION = "cristhian" # version
PROXY = "" # used with  providers-test-proxy.py script in the extras directory

# List of desired providers and their configuration files
# Alias methods will be called in the order of this list
PROVIDERS = [
    # this is up here because it can produce dois
    ("pubmed", {}),

    # best biblio providers go here, in order with best first
    ("arxiv", {}),
    ("crossref", {}),
    ("dryad", {}),            
    ("figshare", {}),            
    ("github", {}),
    ("github_account", {}),
    ("publons", {}),
    ("slideshare", {}),
    ("slideshare_account", {}),
    ("twitter", {}),
    ("vimeo", {}),
    ("youtube", {}),

    # if-need-be biblio providers go here, in order with best first
    ("mendeley", {}),
    ("bibtex", {}),
    ("webpage", {}),

    # don't-have-biblio providers go here, alphabetical order
    ("altmetric_com", {}),    
    ("citeulike", {}),   
    ("delicious", {}),   
    ("plosalm", {}),
    ("plossearch", {}),
    ("scopus", {}),
    ("wikipedia", {}),
]

