class Cache(object):
    def http_get(self, url):
        return None
        
    def cache_http_get(self, url, content):
        pass
        
    def get_cache_timeout_response(self,
                                    url,
                                    http_timeout_in_seconds = 20,
                                    max_cache_age_seconds = (1) * (24 * 60 * 60), # (number of days) * (number of seconds in a day),
                                    header_addons = {}):

        key = hashlib.md5(url).hexdigest()
        mc = memcache.Client(['127.0.0.1:11211'])
        response = mc.get(key)
        if response:
            self.status["count_got_response_from_cache"] += 1
        else:
            http = httplib2.Http(timeout=http_timeout_in_seconds)
            response = http.request(url)
            mc.set(key, response, max_cache_age_seconds)
            self.status["count_api_requests"] += 1

        # This is the old, file-based caching system.
        # I left some stuff out; Heather, feel free to move up.
        '''
        cache_read = http_cached.cache.get(url)
                self.status["count_got_response_from_cache"] += 1
        if (cache_read):
            (response, content) = cache_read.split("\r\n\r\n", 1)
        else:
            ## response['cache-control'] = "max-age=" + str(max_cache_age_seconds)
            ## httplib2._updateCache(header_dict, response, content, http_cached.cache, url)
            if response.fromcache:
            else:
                self.status["count_missed_cache"] += 1
                self.status["count_cache_miss_details"] = str(self.status["count_cache_miss_details"]) + "; " + url
                self.status["count_cache_miss_response"] = str(response)
                self.status["count_api_requests"] += 1

            if False:
                self.status["count_request_exception"] = "EXCEPTION!"
                self.status["count_uncached_call"] += 1
                self.status["count_api_requests"] += 1
                #(response, content) = http_cached.request(url, headers=header_dict.update({'cache-control':'no-cache'}))
                req = urllib2.Request(url, headers=header_dict)
                uh = urllib2.urlopen(req)
                content = uh.read()
                response = uh.info()
        '''

        return(response)