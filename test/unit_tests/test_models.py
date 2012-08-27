from nose.tools import raises, assert_equals, nottest
import os, unittest, hashlib, json, pprint
from time import sleep
from werkzeug.security import generate_password_hash
from totalimpact import models, dao, tiredis
from totalimpact.providers import bibtex, github

COLLECTION_DATA = {
    "_id": "uuid-goes-here",
    "collection_name": "My Collection",
    "owner": "abcdef",
    "created": 1328569452.406,
    "last_modified": 1328569492.406,
    "item_tiids": ["origtiid1", "origtiid2"] 
    }

ALIAS_DATA = {
    "title":["Why Most Published Research Findings Are False"],
    "url":["http://www.plosmedicine.org/article/info:doi/10.1371/journal.pmed.0020124"],
    "doi": ["10.1371/journal.pmed.0020124"]
    }

ALIAS_CANONICAL_DATA = {
    "title":["Why Most Published Research Findings Are False"],
    "url":["http://www.plosmedicine.org/article/info:doi/10.1371/journal.pmed.0020124"],
    "doi": ["10.1371/journal.pmed.0020124"]
    }


STATIC_META = {
        "display_name": "readers",
        "provider": "Mendeley",
        "provider_url": "http://www.mendeley.com/",
        "description": "Mendeley readers: the number of readers of the article",
        "icon": "http://www.mendeley.com/favicon.ico",
        "category": "bookmark",
        "can_use_commercially": "0",
        "can_embed": "1",
        "can_aggregate": "1",
        "other_terms_of_use": "Must show logo and say 'Powered by Santa'",
        }

KEY1 = "8888888888.8"
KEY2 = "9999999999.9"
VAL1 = 1
VAL2 = 2

METRICS_DATA = {
    "ignore": False,
    "static_meta": STATIC_META,
    "provenance_url": ["http://api.mendeley.com/research/public-chemical-compound-databases/"],
    "values":{
        KEY1: VAL1,
        KEY2: VAL2
    }
}

METRICS_DATA2 = {
    "ignore": False,
    "latest_value": 21,
    "static_meta": STATIC_META,
    "provenance_url": ["http://api.mendeley.com/research/public-chemical-compound-databases/"],
    "values":{
        KEY1: VAL1,
        KEY2: VAL2
    }
} 

METRICS_DATA3 = {
    "ignore": False,
    "latest_value": 31,
    "static_meta": STATIC_META,
    "provenance_url": ["http://api.mendeley.com/research/public-chemical-compound-databases/"],
    "values":{
        KEY1: VAL1,
        KEY2: VAL2
    }
}

METRIC_NAMES = ["foo:views", "bar:views", "bar:downloads", "baz:sparkles"]


BIBLIO_DATA = {
        "title": "An extension of de Finetti's theorem", 
        "journal": "Advances in Applied Probability", 
        "author": [
            "Pitman, J"
            ], 
        "collection": "pitnoid", 
        "volume": "10", 
        "id": "p78",
        "year": "1978",
        "pages": "268 to 270"
    }


ITEM_DATA = {
    "_id": "test",
    "created": 1330260456.916,
    "last_modified": 12414214.234,
    "aliases": ALIAS_DATA,
    "metrics": { 
        "wikipedia:mentions": METRICS_DATA,
        "bar:views": METRICS_DATA2
    },
    "biblio": BIBLIO_DATA,
    "type": "item"
}

TEST_PROVIDER_CONFIG = [
    ("wikipedia", {})
]



class TestItemFactory():

    def setUp(self):
        # hacky way to delete the "ti" db, then make it fresh again for each test.
        temp_dao = dao.Dao("http://localhost:5984", os.getenv("CLOUDANT_DB"))
        temp_dao.delete_db(os.getenv("CLOUDANT_DB"))
        self.d = dao.Dao("http://localhost:5984", os.getenv("CLOUDANT_DB"))
        self.myrefsets = {"nih": {"2011": {
                        "facebook:comments": {0: [1, 99], 1: [91, 99]}, "mendeley:groups": {0: [1, 99], 3: [91, 99]}
                    }}}

#    def test_make_new(self):
#        '''create an item from scratch.'''
#        item = models.ItemFactory.make()
#        assert_equals(len(item["_id"]), 24)
#        assert item["created"] < datetime.datetime.now().isoformat()
#        assert_equals(item["aliases"], {})


    def test_adds_genre(self):
        # put the item in the db
        self.d.save(ITEM_DATA)
        item = models.ItemFactory.get_item("test", self.myrefsets, self.d)
        assert_equals(item["biblio"]['genre'], "article")

    def test_get_metric_names(self):
        response = models.ItemFactory.get_metric_names(TEST_PROVIDER_CONFIG)
        assert_equals(response, ['wikipedia:mentions'])


    def test_decide_genre_article_doi(self):
        aliases = {"doi":["10:123", "10:456"]}
        genre = models.ItemFactory.decide_genre(aliases)
        assert_equals(genre, "article")

    def test_decide_genre_article_pmid(self):
        aliases = {"pmid":["12345678"]}
        genre = models.ItemFactory.decide_genre(aliases)
        assert_equals(genre, "article")

    def test_decide_genre_slides(self):
        aliases = {"url":["http://www.slideshare.net/jason/my-slides"]}
        genre = models.ItemFactory.decide_genre(aliases)
        assert_equals(genre, "slides")

    def test_decide_genre_software(self):
        aliases = {"url":["http://www.github.com/jasonpriem/my-sofware"]}
        genre = models.ItemFactory.decide_genre(aliases)
        assert_equals(genre, "software")

    def test_decide_genre_dataset(self):
        aliases = {"doi":["10.5061/dryad.18"]}
        genre = models.ItemFactory.decide_genre(aliases)
        assert_equals(genre, "dataset")

    def test_decide_genre_webpage(self):
        aliases = {"url":["http://www.google.com"]}
        genre = models.ItemFactory.decide_genre(aliases)
        assert_equals(genre, "webpage")

    def test_decide_genre_unknown(self):
        aliases = {"unknown_namespace":["myname"]}
        genre = models.ItemFactory.decide_genre(aliases)
        assert_equals(genre, "unknown")

    def test_build_item_for_client(self):
        item = {'created': '2012-08-23T14:40:16.399932', '_rev': '6-3e0ede6e797af40860e9dadfb39056ce', 'providersWithMetricsCount': 11, 'last_modified': '2012-08-23T14:40:16.399932', 'biblio': {'title': 'Perceptual training strongly improves visual motion perception in schizophrenia', 'journal': 'Brain and Cognition', 'year': 2011, 'authors': u'Norton, McBain, \xd6ng\xfcr, Chen'}, '_id': '4mlln04q1rxy6l9oeb3t7ftv', 'type': 'item', 'aliases': {'url': ['http://linkinghub.elsevier.com/retrieve/pii/S0278262611001308', 'http://www.ncbi.nlm.nih.gov/pubmed/21872380'], 'pmid': ['21872380'], 'doi': ['10.1016/j.bandc.2011.08.003'], 'title': ['Perceptual training strongly improves visual motion perception in schizophrenia']}}
        snaps = [{'tiid': '4mlln04q1rxy6l9oeb3t7ftv', 'metric_name': 'mendeley:groups', 'created': '2012-08-23T21:41:05.526046', '_rev': '1-5fde8dbb5c3af04114adb18295a42259', 'value': 2, 'drilldown_url': 'http://api.mendeley.com/research/perceptual-training-strongly-improves-visual-motion-perception-schizophrenia/', '_id': '25gvr5xxvbu8mabgzvvkdf65', 'type': 'metric_snap'}]
        response = models.ItemFactory.build_item_for_client(item, snaps, self.myrefsets)

        expected = {'raw': 2, '2012-08-23T21:41:05.526046': 2, 'nih': [91, 99]}
        assert_equals(response["metrics"]['mendeley:groups']["values"], expected)




class TestMemberItems():


    def setUp(self):
        # setup a clean new redis instance
        self.r = tiredis.from_url("redis://localhost:6379")
        self.r.flushdb()

        bibtex.Bibtex.paginate = lambda self, x: [1,2,3,4]
        bibtex.Bibtex.member_items = lambda self, x: ("doi", str(x))
        self.memberitems_resp = [
            ["doi", "1"],
            ["doi", "2"],
            ["doi", "3"],
            ["doi", "4"],
        ]

        self.mi = models.MemberItems(bibtex.Bibtex(), self.r)

    def test_init(self):
        assert_equals(self.mi.__class__.__name__, "MemberItems")
        assert_equals(self.mi.provider.__class__.__name__, "Bibtex")

    def test_start_update(self):
        ret = self.mi.start_update("1234")
        input_hash = hashlib.md5("1234").hexdigest()
        assert_equals(input_hash, ret)

        sleep(.1) # give the thread a chance to finish.
        status = json.loads(self.r.get(input_hash))

        assert_equals(status["memberitems"], self.memberitems_resp )
        assert_equals(status["complete"], 4 )

    def test_get_sync(self):

        github.Github.member_items = lambda self, x: \
                [("github", name) for name in ["project1", "project2", "project3"]]
        synch_mi = models.MemberItems(github.Github(), self.r)

        # we haven't put q in redis with MemberItems.start_update(q),
        # so this should update while we wait.
        ret = synch_mi.get_sync("jasonpriem")
        assert_equals(ret["pages"], 1)
        assert_equals(ret["complete"], 1)
        assert_equals(ret["memberitems"],
            [
                ("github", "project1"),
                ("github", "project2"),
                ("github", "project3")
            ]
        )


    def test_get_async(self):
        ret = self.mi.start_update("1234")
        sleep(.1)
        res = self.mi.get_async(ret)
        print res
        assert_equals(res["complete"], 4)
        assert_equals(res["memberitems"], self.memberitems_resp)

class TestUserFactory():
    def setUp(self):
        # hacky way to delete the "ti" db, then make it fresh again for each test.
        temp_dao = dao.Dao("http://localhost:5984", os.getenv("CLOUDANT_DB"))
        temp_dao.delete_db(os.getenv("CLOUDANT_DB"))
        self.d = dao.Dao("http://localhost:5984", os.getenv("CLOUDANT_DB"))

        self.id = "ovid@rome.it"
        self.key = "ahashgeneratedbytheclient"

        self.user_doc = {
            "_id": self.id,
            "key": self.key,
            "colls": {
                "cid1": "key1",
                "cid2": "key2"
            }
        }
        self.d.save(self.user_doc)

    def test_get(self):
        user_dict = models.UserFactory.get(self.id, self.d, self.key)
        print user_dict
        assert_equals(user_dict, self.user_doc)

    @raises(models.NotAuthenticatedError)
    def test_get_when_pw_is_wrong(self):
        user_dict = models.UserFactory.get(self.id, self.d, "wrong password")

    @raises(KeyError)
    def test_get_when_username_is_wrong(self):
        user_dict = models.UserFactory.get("wrong email", self.d, self.key)

    def test_create(self):
        self.user_doc["_id"] = "new person"
        doc = models.UserFactory.put(self.user_doc, self.key, self.d)
        assert_equals("new person",doc["_id"] )
        assert_equals(self.key, doc["key"] )

    def test_update_user(self):

        # modify the user, then put it again
        self.user_doc["colls"]["cid3"] = "key3"
        models.UserFactory.put(self.user_doc, self.key, self.d)

        updated_user = models.UserFactory.get("ovid@rome.it", self.d, self.key)
        assert_equals(
            updated_user["colls"],
            {"cid1": "key1", "cid2":"key2", "cid3":"key3"}
        )

