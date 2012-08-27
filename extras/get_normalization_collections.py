import random_pmids

query_template = "(Research Support, U.S. Gov't, P.H.S. [pt] OR nih [gr]) AND Journal Article[pt] AND {year}[dp]"
sample_size = 50
seed = 41
email = "team@total-impact.org"

for year in range(2011, 2012):
	print "\n\n"
	print year
	query = query_template.format(year=year)
	print query
	pmids = random_pmids.get_random_pmids(sample_size, email, query, seed)


#Useful references for queries:
#http://www.nlm.nih.gov/bsd/funding_support.html
#http://www.nlm.nih.gov/bsd/grant_acronym.html#pub_health

# (Research Support, U.S. Gov't, P.H.S. [pt] OR nih [gr]) AND Journal Article[pt] AND 2010[dp]


#Useful references for queries:
#http://www.nlm.nih.gov/bsd/funding_support.html
#http://www.nlm.nih.gov/bsd/grant_acronym.html#pub_health

# (Research Support, U.S. Gov't, P.H.S. [pt] OR nih [gr]) AND Journal Article[pt] AND 2010[dp]

