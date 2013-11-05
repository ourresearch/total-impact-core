import argparse
import requests
import logging
import os
import sys
import json
import re

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='[%(process)d] %(levelname)8s %(threadName)30s %(name)s - %(message)s'
)
logger = logging.getLogger("try_scopus")



if __name__ == '__main__':
    # get args from the command line:
    parser = argparse.ArgumentParser(description="try pmc")

    url = "http://api.elsevier.com/content/search/index:SCOPUS?query=DOI(10.1016/j.stem.2011.10.002)&field=citedby-count&apiKey=" + os.environ["SCOPUS_KEY"]
    print url
    response = requests.get(url)
    print response.text
    


