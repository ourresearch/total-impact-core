import couchdb
import argparse
import requests
import logging
import os
import sys
import json
import re
import datetime
import calendar
from totalimpact import provider_batch_data

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='[%(process)d] %(levelname)8s %(threadName)30s %(name)s - %(message)s'
)
logger = logging.getLogger("load_batch_pmc")

def last_minute_of_a_month(year, month):
    first_day = datetime.datetime(year, month, 1)
    number_of_days = calendar.monthrange(year, month)[1]
    first_day_next_month = first_day + datetime.timedelta(days=number_of_days)
    last_day_last_minute = first_day_next_month - datetime.timedelta(microseconds=1)
    return last_day_last_minute

def build_batch_dict(page, options_dict):
    pmids = re.findall('pubmed-id="(\d{2,20})"', page)

    year = int(options_dict["year"])
    month = int(options_dict["month"])
    min_date = datetime.datetime(year, month, 1)
    max_date = last_minute_of_a_month(year, month)
    batch_dict = {
       "_id": "pmc{year}{month}".format(**options_dict),
       "type": "provider_data_dump",
       "provider": "pmc",
       "provider_raw_version": 1,
       "created": datetime.datetime.now().isoformat(),
       "min_event_date": min_date.isoformat(),
       "max_event_date": max_date.isoformat(),
       "aliases": {
           "pmid": pmids
       },
       "raw": page
    }
    return batch_dict

def get_pmc_stats_page(options_dict):
    #add leading zero if not given
    if len(str(options_dict["month"]))==1:
        options_dict["month"] = "0" + str(options_dict["month"])

    pmc_download_template = "http://www.pubmedcentral.nih.gov/utils/publisher/pmcstat/pmcstat.cgi?year={year}&month={month}&jrid={journal}&form=xml&user={user}&password={password}"
    url = pmc_download_template.format(**options_dict)
    print url
    resp = requests.get(url)
    page = resp.text
    return page

def write_batch_dict(batch_dict):
    logger.info("connected to postgres at " + os.getenv("POSTGRESQL_URL"))
    new_object = provider_batch_data.create_objects_from_doc(batch_dict)
    print "added to db if it wasn't already there"

    print "current batch data:"
    matches = provider_batch_data.ProviderBatchData.query.filter_by(provider="pmc").order_by("min_event_date").all()
    for match in matches:
        print match        




if __name__ == '__main__':
    # get args from the command line:
    parser = argparse.ArgumentParser(description="Import PMC monthly stats")
    parser.add_argument("-y", "--year", default="2013")
    parser.add_argument("-m", "--month", required=True)
    parser.add_argument("-j", "--journal", default="elife")
    parser.add_argument("-u", "--user", default="elife_pmc")
    parser.add_argument("-p", "--password", required=True)

    options_dict = vars(parser.parse_args())
    print options_dict

    page = get_pmc_stats_page(options_dict)
    batch_dict = build_batch_dict(page, options_dict)
    print(json.dumps(batch_dict, indent=4))
    if batch_dict["aliases"]["pmid"]:
        write_batch_dict(batch_dict)
    else:
        print "no data for this month, not saving anything"




