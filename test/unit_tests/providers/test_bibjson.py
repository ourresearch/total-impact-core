from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError, ProviderServerError


import os, json
from nose.tools import assert_equals, raises, nottest


SAMPLE_EXTRACT_MEMBER_ITEMS_SHORT =  [
  {
           "authors": [
               {
                   "name": "H A Piwowar"
               }, 
               {
                   "name": "W W Chapman"
               }
           ], 
           "booktitle": "AMIA Annual Symposium proceedings / AMIA Symposium. AMIA Symposium,", 
           "marker": "Piwowar, Chapman, 2008", 
           "pages": "596--600", 
           "rawString": "Piwowar, H.A. and Chapman, W.W., (2008). Identifying data sharing in biomedical literature., AMIA Annual Symposium proceedings / AMIA Symposium. AMIA Symposium, pp. 596-600", 
           "title": "Identifying data sharing in biomedical literature.,", 
           "year": "2008"
       }, 
       {
           "authors": [
               {
                   "name": "H A Piwowar"
               }, 
               {
                   "name": "W W Chapman"
               }
           ], 
           "journal": "Journal of Informetrics,", 
           "marker": "Piwowar, Chapman, 2010", 
           "pages": "148--156", 
           "rawString": "Piwowar, H.A. and Chapman, W.W., (2010). Public sharing of research datasets: A pilot study of associations, Journal of Informetrics, vol. 4, no. 2, pp. 148-156", 
           "title": "Public sharing of research datasets: A pilot study of associations,", 
           "volume": "4", 
           "year": "2010"
       }
   ]



class TestBibjson(ProviderTestCase):

    provider_name = "bibjson"

    def setUp(self):
        ProviderTestCase.setUp(self)

    def test_member_items(self):
        file_contents = SAMPLE_EXTRACT_MEMBER_ITEMS_SHORT
        response = self.provider.member_items(file_contents)

        print json.dumps(response, indent=4)

        expected = [
              (
                  "biblio", 
                  {
                      "rawString": "Piwowar, H.A. and Chapman, W.W., (2008). Identifying data sharing in biomedical literature., AMIA Annual Symposium proceedings / AMIA Symposium. AMIA Symposium, pp. 596-600", 
                      "title": "AMIA Annual Symposium proceedings / AMIA Symposium. AMIA Symposium,", 
                      "first_author": "Piwowar", 
                      "booktitle": "AMIA Annual Symposium proceedings / AMIA Symposium. AMIA Symposium,", 
                      "year": "2008", 
                      "first_page": "596", 
                      "authors": "Piwowar, Chapman", 
                      "marker": "Piwowar, Chapman, 2008", 
                      "pages": "596--600"
                  }
              ), 
              (
                  "biblio", 
                  {
                      "volume": "4", 
                      "first_author": "Piwowar", 
                      "first_page": "148", 
                      "rawString": "Piwowar, H.A. and Chapman, W.W., (2010). Public sharing of research datasets: A pilot study of associations, Journal of Informetrics, vol. 4, no. 2, pp. 148-156", 
                      "authors": "Piwowar, Chapman", 
                      "marker": "Piwowar, Chapman, 2010", 
                      "journal": "Journal of Informetrics,", 
                      "title": "Public sharing of research datasets: A pilot study of associations,", 
                      "year": "2010", 
                      "pages": "148--156"
                  }
              )
          ]
        assert_equals(response, expected)

