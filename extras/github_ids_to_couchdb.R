library(digest)
library(RCurl)
library(RJSONIO)
setwd("~/Downloads")
d <- read.csv("github_users.csv")

# 1. prepare the data
#####################

# remove duplicates
d <- unique(d)
nrow(d) # 177576; seems there were a ton of duplicates...

# Each new Couch doc needs a unique _id value. So we add a new column filled
# by each username's md5 hash.
d[,"_id"] <- apply(d, 1, digest) 
d["actor"] <- as.character(d$actor)
head(d)

# uploading 170k+ docs individually to CouchDB means 170k+ HTTP requests, which
# would take forever. So we'll group these into 1000-item chunks to take advantage
# of Couch's bulk-upload feature.
group_size <- 1000
num_groups <- ceiling(nrow(d) / group_size)
chunks <- split(d, sample(rep(1:num_groups, group_size)))
chunks[[1]][1:10,]


# 2. updload to couchdb
#######################

# setup the urls we'll use and test
db_url <- "https://total-impact:<PASSWORD>@total-impact.cloudant.com/github_usernames"
getURL(db_url) # ping couch, make sure it works
req_url <- paste(db_url, "/_bulk_docs", sep="")

# takes a dataframe with columns for github users and ids; uploads each
# row as a couchdb doc in one http call.
upload_chunk = function(chunk) {
	json_rows = toJSON(split(chunk, 1:nrow(chunk)), .withNames=F)
	post_fields = paste('{"docs": ', json_rows,'}')
	response <- fromJSON(getURL(
		req_url,
		customrequest="POST",
		httpheader=c('Content-Type'='application/json'),
  		postfields= post_fields
	))
	return(response)
}

# run the upload_chunks function on all the chunks
sapply(chunks, upload_chunk)
