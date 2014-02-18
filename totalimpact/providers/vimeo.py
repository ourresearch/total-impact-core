from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import simplejson, os, re

import logging
logger = logging.getLogger('ti.providers.vimeo')

class Vimeo(Provider):  

    example_id = ("url", "http://vimeo.com/48605764")

    url = "http://vimeo.com"
    descr = "Vimeo: Your videos belong here."
    biblio_url_template = "http://vimeo.com/api/v2/video/%s.json"
    aliases_url_template = "http://vimeo.com/api/v2/video/%s.json"
    metrics_url_template = "http://vimeo.com/api/v2/video/%s.json"
    provenance_url_template = "http://vimeo.com/%s"

    static_meta_dict = {
        "plays": {
            "display_name": "plays",
            "provider": "Vimeo",
            "provider_url": "http://vimeo.com",
            "description": "The number of people who have played the video",
            "icon": "https://secure-a.vimeocdn.com/images_v6/favicon_32.ico",
        },
        "likes": {
            "display_name": "likes",
            "provider": "Vimeo",
            "provider_url": "http://vimeo.com",
            "description": "The number of people who have 'liked' the video",
            "icon": "https://secure-a.vimeocdn.com/images_v6/favicon_32.ico",
            },
        "comments": {
            "display_name": "comments",
            "provider": "Vimeo",
            "provider_url": "http://vimeo.com",
            "description": "The number of comments on a video",
            "icon": "https://secure-a.vimeocdn.com/images_v6/favicon_32.ico",
            }
    }     

    def __init__(self):
        super(Vimeo, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        if (("url" == namespace) and ("vimeo.com/" in nid)):
            return True
        else:
            return False

    def _get_video_id(self, video_url):
        try:
            nid_as_vimeo_id = re.findall("vimeo.com\/(\d+)", video_url)[0]
        except IndexError:
            raise ProviderContentMalformedError("No recognizable vimeo id")
        return nid_as_vimeo_id

    #override because need to break up id
    def _get_templated_url(self, template, nid_as_video_url, method=None):
        nid_as_video_id = self._get_video_id(nid_as_video_url)
        url = template % (nid_as_video_id)
        return(url)

    def _extract_biblio(self, page, id=None):

        json_response = provider._load_json(page)
        this_video_json = json_response[0]

        dict_of_keylists = {
            'title':        ['title'],
            'authors':      ['user_name'],
            'published_date': ['upload_date'],
            'url':          ['url']
        }

        biblio_dict = provider._extract_from_data_dict(this_video_json, dict_of_keylists)

        try:
            biblio_dict["year"] = biblio_dict["published_date"][0:4]
        except KeyError:
            pass

        biblio_dict["repository"] = "Vimeo"

        return biblio_dict    


    def _extract_metrics(self, page, status_code=200, id=None):        
        if status_code != 200:
            if status_code == 404:
                return {}
            else:
                raise(self._get_error(status_code))

        if not "user_id" in page:
            raise ProviderContentMalformedError

        json_response = provider._load_json(page)
        this_video_json = json_response[0]

        dict_of_keylists = {
            'vimeo:plays' : ['stats_number_of_plays'],
            'vimeo:likes' : ['stats_number_of_likes'],
            'vimeo:comments' : ['stats_number_of_comments']
        }

        metrics_dict = provider._extract_from_data_dict(this_video_json, dict_of_keylists)

        return metrics_dict
