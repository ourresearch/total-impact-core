from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import simplejson, os, re

import logging
logger = logging.getLogger('ti.providers.youtube')

class Youtube(Provider):  

    example_id = ("youtube", "http://www.youtube.com/watch?v=d39DL4ed754")

    url = "http://youtube.com"
    descr = "YouTube allows billions of people to discover, watch and share originally-created videos"
    biblio_url_template = "https://www.googleapis.com/youtube/v3/videos?id=%s&part=snippet,statistics&key=" + os.environ["YOUTUBE_KEY"]
    aliases_url_template = "https://www.googleapis.com/youtube/v3/videos?id=%s&part=snippet,statistics&key=" + os.environ["YOUTUBE_KEY"]
    metrics_url_template = "https://www.googleapis.com/youtube/v3/videos?id=%s&part=snippet,statistics&key=" + os.environ["YOUTUBE_KEY"]
    provenance_url_template = "http://www.youtube.com/watch?v=%s"

    static_meta_dict = {
        "views": {
            "display_name": "views",
            "provider": "YouTube",
            "provider_url": "http://youtube.com",
            "description": "The number of people who have viewed the video",
            "icon": "http://www.youtube.com/favicon.ico",
        },
        "likes": {
            "display_name": "likes",
            "provider": "YouTube",
            "provider_url": "http://youtube.com",
            "description": "The number of people who have 'liked' the video",
            "icon": "http://www.youtube.com/favicon.ico",
            },
        "dislikes": {
            "display_name": "dislikes",
            "provider": "YouTube",
            "provider_url": "http://youtube.com",
            "description": "The number of people who have who have 'disliked' the video",
            "icon": "http://www.youtube.com/favicon.ico",
            },
        "favorites": {
            "display_name": "favorites",
            "provider": "YouTube",
            "provider_url": "http://youtube.com",
            "description": "The number of people who have marked the video as a favorite",
            "icon": "http://www.youtube.com/favicon.ico",
            },
        "comments": {
            "display_name": "comments",
            "provider": "YouTube",
            "provider_url": "http://youtube.com",
            "description": "The number of comments on a video",
            "icon": "http://www.youtube.com/favicon.ico",
            }
    }     

    def __init__(self):
        super(Youtube, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        if (("url" == namespace) and ("youtube.com/" in nid)):
            nid_as_youtube_url = self._get_video_id(nid)
            if nid_as_youtube_url:
                return True
        return False

    def _get_video_id(self, video_url):
        match = re.findall("watch.*[\?|&]v=([\dA-Za-z_\-]+)", video_url)
        try:
            nid_as_youtube_url = match[0]
        except IndexError:
            nid_as_youtube_url = None
            logging.error(u"couldn't get video_id for {video_url}".format(
                video_url=video_url))
        return nid_as_youtube_url

    #override because need to break up id
    def _get_templated_url(self, template, nid_as_youtube_url, method=None):
        nid_as_video_id = self._get_video_id(nid_as_youtube_url)
        if not nid_as_video_id:
            raise ProviderContentMalformedError
        url = template % (nid_as_video_id)
        return(url)

    def _extract_biblio(self, page, id=None):

        if not "snippet" in page:
            raise ProviderContentMalformedError

        json_response = provider._load_json(page)
        this_video_json = json_response["items"][0]

        dict_of_keylists = {
            'title': ['snippet', 'title'],
            'channel_title': ['snippet', 'channelTitle'],
            'published_date': ['snippet', 'publishedAt']
        }

        biblio_dict = provider._extract_from_data_dict(this_video_json, dict_of_keylists)

        try:
            biblio_dict["year"] = biblio_dict["published_date"][0:4]
        except KeyError:
            pass

        biblio_dict["url"] = id
        biblio_dict["repository"] = "YouTube"

        return biblio_dict    


    def _extract_metrics(self, page, status_code=200, id=None):        
        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))

        if not "snippet" in page:
            raise ProviderContentMalformedError

        json_response = provider._load_json(page)
        this_video_json = json_response["items"][0]

        dict_of_keylists = {
            'youtube:views' : ['statistics', 'viewCount'],
            'youtube:likes' : ['statistics', 'likeCount'],
            'youtube:dislikes' : ['statistics', 'dislikeCount'],
            'youtube:favorites' : ['statistics', 'favoriteCount'],
            'youtube:comments' : ['statistics', 'commentCount'],
        }

        metrics_dict = provider._extract_from_data_dict(this_video_json, dict_of_keylists)

        metrics_dict = provider._metrics_dict_as_ints(metrics_dict)

        return metrics_dict
