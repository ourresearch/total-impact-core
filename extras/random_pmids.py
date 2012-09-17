import os
import re
import argparse
import requests
import time
import BeautifulSoup
import random

""" Returns random PubMed IDs that match a given PubMed query. """

# Please read NCBI eUtils Terms of Use: http://www.ncbi.nlm.nih.gov/books/NBK25497/#chapter2.Usage_Guidelines_and_Requiremen
# At the time of this writing, it includes:
""" NCBI recommends that users post no more than three URL requests per second 
and limit large jobs to either weekends or between 9:00 PM and 5:00 AM Eastern time 
during weekdays. Failure to comply with this policy may result in an IP address being 
blocked from accessing NCBI. If NCBI blocks an IP address, service will not be restored 
unless the developers of the software accessing the E-utilities register values of 
the tool and email parameters with NCBI"""

def parse_random_doi_args():
	# get args from the command line:
	parser = argparse.ArgumentParser(description="""Returns random PubMed IDs that match a given PubMed query.  
		May contain duplicates.
		Returns three PMIDs per second""")
	parser.add_argument("sample_size", type=int, help="number of PubMed IDs to return")
	parser.add_argument("email", type=str, help="email address to send in api request to NCBI")
	parser.add_argument("query", type=str, help="query to filter PubMed IDs (surround the query with 'single quotes')")
	parser.add_argument("--seed", type=str, help='seed for random numbers, for reproducability.  (default is no set seed.  Example seed: 42)')
	args = parser.parse_args()
	return args

url_template = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&email={email}&term={query}&retmax=1&retstart={random_index}"

def get_nth_pmid(index, query, email):
	url = url_template.format(random_index=index, query=query, email=email)
	r = requests.get(url)
	return(r)

def get_random_pmids(sample_size, email, query, seed=None):
	# Do an initial query to get the total number of hits
	url = url_template.format(random_index=1, query=query, email=email)
	r = requests.get(url)
	initial_response = r.text
	soup = BeautifulSoup.BeautifulStoneSoup(initial_response)
	translated_query = soup.querytranslation.string
	population_size = int(soup.esearchresult.count.string)

	print "Double-check PubMed's translation of your query: %s" %translated_query
	print "Number of PMIDs returned by this query: %i" %population_size
	print "Off to randomly sample %i of them!" %sample_size

	if seed:
		random.seed(seed)
		print "Seed has been set before sampling."

	pmid_pattern = re.compile("<Id>(?P<pmid>\d+)</Id>")  # do this as an re because it is simple and fast

	if sample_size > population_size:
		print "sample size is bigger than population size, so using population size"
		sample_size = population_size
	random_indexes = random.sample(range(1, population_size), sample_size)

	pmids = []
	for random_index in random_indexes:
		r = get_nth_pmid(random_index, query, email)
		try:
			pmid = pmid_pattern.search(r.text).group("pmid")

		#hope this is transient, try the random number + 1
		except AttributeError:
			print "got an error extracting pmid, trying again with subsequent index"
			r = get_nth_pmid(random_index+1, query, email)
			pmid = pmid_pattern.search(r.text).group("pmid")

		print "pmid:" + pmid
		pmids.append(pmid)
		time.sleep(1/3)  #NCBI requests no more than three requests per second at http://www.ncbi.nlm.nih.gov/books/NBK25497/#chapter2.Usage_Guidelines_and_Requiremen
	return pmids

if __name__ == '__main__':
	args = parse_random_doi_args()
	pmids = get_random_pmids(args.sample_size, args.email, args.query, args.seed)


