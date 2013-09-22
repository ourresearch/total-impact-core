from nose.tools import raises, assert_equals, assert_true, nottest
import os, unittest, hashlib, json, pprint, datetime
from time import sleep
from werkzeug.security import generate_password_hash
from totalimpact import models, tiredis
from totalimpact import db, app
from totalimpact import item as item_module
from totalimpact.item import Item, Metric, Biblio, Alias
from totalimpact.providers import bibtex, github
from test.utils import setup_postgres_for_unittests, teardown_postgres_for_unittests


class TestItem():

    def setUp(self):
        self.BIBLIO_DATA = {
            "title": "An extension of de Finetti's theorem",
            "journal": "Advances in Applied Probability",
            "author": [
                "Pitman, J"
            ],
            "authors": "Pitman",
            "collection": "pitnoid",
            "volume": "10",
            "id": "p78",
            "year": "1978",
            "pages": "268 to 270"
        }

        ALIAS_DATA = {
            "title":["Why Most Published Research Findings Are False"],
            "url":["http://www.plosmedicine.org/article/info:doi/10.1371/journal.pmed.0020124"],
            "doi": ["10.1371/journal.pmed.0020124"],
            "biblio": [self.BIBLIO_DATA]
        }


        self.KEY1 = '2012-08-23T14:40:16.888888'
        self.KEY2 = '2012-08-23T14:40:16.999999'
        self.VAL1 = 1
        self.VAL2 = 2

        METRICS_DATA = {
            "provenance_url": "http://api.mendeley.com/research/public-chemical-compound-databases/",
            "values":{
                "raw": self.VAL2,
                "raw_history": {
                    self.KEY1: self.VAL1,
                    self.KEY2: self.VAL2
                }
            }
        }

        METRICS_DATA2 = {
            "provenance_url": "http://api.mendeley.com/research/public-chemical-compound-databases/",
            "values":{
                "raw": self.VAL2,
                "raw_history": {
                    self.KEY1: self.VAL1,
                    self.KEY2: self.VAL2
                }
            }
        }

        METRICS_DATA3 = {
            "provenance_url": "http://api.mendeley.com/research/public-chemical-compound-databases/",
            "values":{
                "raw": self.VAL2,
                "raw_history": {
                    self.KEY1: self.VAL1,
                    self.KEY2: self.VAL2
                }
            }
        }


        self.ITEM_DATA = {
            "_id": "test",
            "created": '2012-08-23T14:40:16.399932',
            "last_modified": '2012-08-23T14:40:16.399932',
            "aliases": ALIAS_DATA,
            "metrics": {
                "wikipedia:mentions": METRICS_DATA,
                "topsy:tweets": METRICS_DATA2
            },
            "biblio": self.BIBLIO_DATA,
            "type": "item"
        }

        self.TEST_PROVIDER_CONFIG = [
            ("wikipedia", {})
        ]

        self.d = None
        
        self.myrefsets = {"nih": {"2011": {
                        "facebook:comments": {0: [1, 99], 1: [91, 99]}, "mendeley:groups": {0: [1, 99], 3: [91, 99]}
                    }}}

        # setup a clean new redis test database.  We're putting unittest redis at DB Number 8.
        self.r = tiredis.from_url("redis://localhost:6379", db=8)
        self.r.flushdb()


        db.session.execute("""drop view if exists min_biblio""")
        db.session.commit()        

        self.db = setup_postgres_for_unittests(db, app)
        


    def tearDown(self):
        teardown_postgres_for_unittests(self.db)



    def test_init_item_and_add_aliases(self):
        item_object = Item()
        print item_object

        self.db.session.add(item_object)
        self.db.session.commit()

        # we have an item but it has no aliases
        found_item = Item.query.first()
        assert_true(len(found_item.tiid) > 10)
        assert_equals(found_item.aliases, [])

        test_alias = ("doi", "10.123/abc")
        (test_namespace, test_nid) = test_alias

        #make sure nothing there beforehand
        response = Alias.filter_by_alias(test_alias).first()
        assert_equals(response, None)

        new_alias = Alias(alias_tuple=test_alias)
        print new_alias
        self.db.session.add(item_object)
        item_object.aliases = [new_alias]

        # still not there
        response = Alias.filter_by_alias(test_alias).first()
        assert_equals(response, None)

        self.db.session.commit()

        # and now poof there it is
        response = Alias.query.all()
        assert_equals(response[0].alias_tuple, test_alias)

        response = Alias.query.filter_by(nid=test_alias[1]).first()
        assert_equals(response.nid, test_alias[1])

        response = Alias.filter_by_alias(test_alias).first()
        assert_equals(response.alias_tuple, test_alias)

        response = item_module.get_tiid_by_alias(test_namespace, test_nid)
        assert_equals(response, found_item.tiid)


    def test_add_biblio(self):
        new_item = Item()
        tiid = new_item.tiid
        print new_item

        #add biblio
        self.db.session.add(new_item)
        new_biblio_objects = item_module.create_biblio_objects([self.BIBLIO_DATA]) 
        new_item.biblios = new_biblio_objects
        self.db.session.commit()

        # now poof there is biblio
        found_item = Item.query.filter_by(tiid=tiid).first()
        expected = [u'10', u'Pitman', u"An extension of de Finetti's theorem", u'Advances in Applied Probability', [u"Pitman, J"], u'1978', u'p78', u'pitnoid', u'268 to 270']
        assert_equals([bib.biblio_value for bib in found_item.biblios], expected)
        
        assert_equals(Biblio.as_dict_by_tiid(tiid), self.BIBLIO_DATA)


    def test_get_tiid_by_biblio(self):
        result = self.db.session.execute("""create view min_biblio as (
                    select 
                        a.tiid, 
                        a.provider, 
                        a.biblio_value as title, 
                        b.biblio_value as authors, 
                        c.biblio_value as journal, 
                        a.collected_date
                    from biblio a
                    join biblio b using (tiid, provider)
                    join biblio c using (tiid, provider)
                    where 
                    a.biblio_name = 'title'
                    and b.biblio_name = 'authors'
                    and c.biblio_name = 'journal'
                    )""")
        self.db.session.commit()

        new_item = Item()
        self.db.session.add(new_item)
        new_item.biblios = item_module.create_biblio_objects([self.BIBLIO_DATA]) 
        self.db.session.commit()

        found_tiid = item_module.get_tiid_by_biblio(self.BIBLIO_DATA)
        assert_equals(found_tiid, new_item.tiid)


    def test_add_metrics(self):
        test_metrics = {
            "topsy:tweets": {
                "provenance_url": "http://topsy.com/trackback?url=http%3A//elife.elifesciences.org/content/2/e00646",
                "values": {
                    "raw_history": {
                        "2013-03-29T17:57:41.455719": 1,
                        "2013-04-11T12:57:37.260362": 2,
                        "2013-04-19T07:27:23.117982": 3
                        },
                    "raw": 3
                    }
                } 
            }
        new_item = Item()
        tiid = new_item.tiid
        print new_item

        #add metrics
        metric_objects = item_module.create_metric_objects(test_metrics)
        new_item.metrics = metric_objects
        self.db.session.add(new_item)
        self.db.session.commit()

        # now poof there is metrics
        found_item = Item.query.filter_by(tiid=tiid).first()
        expected = "hi"
        assert_equals(len(found_item.metrics), 3)
        assert_equals(found_item.metrics[0].tiid, tiid)
        assert_equals(found_item.metrics[0].provider, "topsy")
        assert_equals(found_item.metrics[0].raw_value, 1)
        
        test_metrics2 =  {
            "mendeley:country": {
               "values": {
                   "raw_history": {
                       "2013-08-26T09:25:32.750867": [
                           {
                               "value": 38,
                               "name": "United States"
                           },
                           {
                               "value": 23,
                               "name": "Germany"
                           },
                           {
                               "value": 15,
                               "name": "Brazil"
                           }
                       ],
                       "2013-08-27T14:57:29.173887": [
                           {
                               "value": 38,
                               "name": "United States"
                           },
                           {
                               "value": 25,
                               "name": "Germany"
                           },
                           {
                               "value": 13,
                               "name": "Brazil"
                           }
                       ]
                   },
                   "raw": [
                       {
                           "value": 38,
                           "name": "United States"
                       },
                       {
                           "value": 25,
                           "name": "Germany"
                       },
                       {
                           "value": 13,
                           "name": "Brazil"
                       }
                   ]
               },
               "provenance_url": "http://www.mendeley.com/research/phylogeny-informative-measuring-power-comparative-methods-2/"
           }
        }

        metric_objects = item_module.create_metric_objects(test_metrics2)
        new_item.metrics += metric_objects
        self.db.session.add(new_item)
        self.db.session.commit()

        # now poof there is metrics
        found_item = Item.query.filter_by(tiid=tiid).first()
        expected = "hi"
        assert_equals(len(found_item.metrics), 5)
        assert_equals(found_item.metrics[4].tiid, tiid)
        assert_equals(found_item.metrics[4].provider, "mendeley")
        expected = [{u'name': u'United States', u'value': 38}, {u'name': u'Germany', u'value': 25}, {u'name': u'Brazil', u'value': 13}]
        assert_equals(found_item.metrics[4].raw_value, expected)



    def test_make_new(self):
        '''create an item from scratch.'''
        item = item_module.make()
        assert_equals(len(item["_id"]), 24)
        assert item["created"] < datetime.datetime.now().isoformat()
        assert_equals(item["aliases"], {})

    def test_adds_genre(self):
        self.TEST_OBJECT = item_module.create_objects_from_item_doc(self.ITEM_DATA)        
        self.db.session.add(self.TEST_OBJECT)
        self.db.session.commit()

        item = item_module.get_item("test", self.myrefsets, self.d)
        assert_equals(item["biblio"]['genre'], "article")

    def test_get_metric_names(self):
        response = item_module.get_metric_names(self.TEST_PROVIDER_CONFIG)
        assert_equals(response, ['wikipedia:mentions'])


    def test_decide_genre_article_doi(self):
        aliases = {"doi":["10:123", "10:456"]}
        (genre, host) = item_module.decide_genre(aliases)
        assert_equals(genre, "article")

    def test_decide_genre_article_pmid(self):
        aliases = {"pmid":["12345678"]}
        (genre, host) = item_module.decide_genre(aliases)
        assert_equals(genre, "article")

    def test_decide_genre_slides(self):
        aliases = {"url":["http://www.slideshare.net/jason/my-slides"]}
        (genre, host) = item_module.decide_genre(aliases)
        assert_equals(genre, "slides")

    def test_decide_genre_software(self):
        aliases = {"url":["http://www.github.com/jasonpriem/my-sofware"]}
        (genre, host) = item_module.decide_genre(aliases)
        assert_equals(genre, "software")

    def test_decide_genre_dataset_dryad(self):
        aliases = {"doi":["10.5061/dryad.18"]}
        (genre, host) = item_module.decide_genre(aliases)
        assert_equals(genre, "dataset")

    def test_decide_genre_dataset_figshare(self):
        aliases = {"doi":["10.6084/m9.figshare.92393"]}
        (genre, host) = item_module.decide_genre(aliases)
        assert_equals(genre, "dataset")

    def test_decide_genre_webpage(self):
        aliases = {"url":["http://www.google.com"]}
        (genre, host) = item_module.decide_genre(aliases)
        assert_equals(genre, "webpage")

    def test_decide_genre_unknown(self):
        aliases = {"unknown_namespace":["myname"]}
        (genre, host) = item_module.decide_genre(aliases)
        assert_equals(genre, "unknown")

    def test_get_biblio_to_update(self):
        first_biblio = {
           "journal": "Space",
           "title": "A real title"
        }        
        other_biblio = {
           "journal": "Earth",
           "title": "A different title"
        }        
        aop_biblio = {
           "journal": "Nature",
           "title": "AOP"
        }
        response = item_module.get_biblio_to_update({}, first_biblio)
        assert_equals(response, first_biblio)

        response = item_module.get_biblio_to_update(first_biblio, other_biblio)
        assert_equals(response, None)

        response = item_module.get_biblio_to_update(aop_biblio, other_biblio)
        assert_equals(response, other_biblio)



    def test_merge_alias_dicts(self):
        aliases1 = {"ns1":["idA", "idB", "id1"]}
        aliases2 = {"ns1":["idA", "id3", "id4"], "ns2":["id1", "id2"]}
        response = item_module.merge_alias_dicts(aliases1, aliases2)
        print response
        expected = {'ns1': ['idA', 'idB', 'id1', 'id3', 'id4'], 'ns2': ['id1', 'id2']}
        assert_equals(response, expected)

    def test_alias_tuples_from_dict(self):
        aliases = {"unknown_namespace":["myname"]}
        alias_tuples = item_module.alias_tuples_from_dict(aliases)
        assert_equals(alias_tuples, [('unknown_namespace', 'myname')])

    def test_alias_dict_from_tuples(self):
        aliases = [('unknown_namespace', 'myname')]
        alias_dict = item_module.alias_dict_from_tuples(aliases)
        assert_equals(alias_dict, {'unknown_namespace': ['myname']})

    def test_as_old_doc(self):
        test_object = item_module.create_objects_from_item_doc(self.ITEM_DATA)        
        new_doc = test_object.as_old_doc()
        print json.dumps(new_doc, sort_keys=True, indent=4)
        print json.dumps(self.ITEM_DATA, sort_keys=True, indent=4)
        assert_equals(new_doc, self.ITEM_DATA)

    def test_build_item_for_client(self):
        item = {'created': '2012-08-23T14:40:16.399932', '_rev': '6-3e0ede6e797af40860e9dadfb39056ce', 'last_modified': '2012-08-23T14:40:16.399932', 'biblio': {'title': 'Perceptual training strongly improves visual motion perception in schizophrenia', 'journal': 'Brain and Cognition', 'year': 2011, 'authors': u'Norton, McBain, \xd6ng\xfcr, Chen'}, '_id': '4mlln04q1rxy6l9oeb3t7ftv', 'type': 'item', 'aliases': {'url': ['http://linkinghub.elsevier.com/retrieve/pii/S0278262611001308', 'http://www.ncbi.nlm.nih.gov/pubmed/21872380'], 'pmid': ['21872380'], 'doi': ['10.1016/j.bandc.2011.08.003'], 'title': ['Perceptual training strongly improves visual motion perception in schizophrenia']}}
        response = item_module.build_item_for_client(item, self.myrefsets, self.d, False)
        assert_equals(set(response.keys()), set(['created', '_rev', 'metrics', 'last_modified', 'biblio', '_id', 'type', 'aliases']))

    def test_build_item_for_client_excludes_history_by_default(self):
        response = item_module.build_item_for_client(self.ITEM_DATA, self.myrefsets, self.d)
        assert_equals(response["metrics"]["wikipedia:mentions"]["values"].keys(), ["raw"])
        assert_equals(response["metrics"]["topsy:tweets"]["values"].keys(), ["raw"])

    def test_build_item_for_client_includes_history_with_arg(self):
        response = item_module.build_item_for_client(
            self.ITEM_DATA,
            self.myrefsets,
            self.d,
            include_history=True
        )
        assert_equals(
            response["metrics"]["wikipedia:mentions"]["values"]["raw_history"][self.KEY1],
            self.VAL1
        )
        assert_equals(
            response["metrics"]["wikipedia:mentions"]["values"]["raw_history"][self.KEY2],
            self.VAL2
        )


    def add_metrics_data(self):
        item = {'created': '2012-08-23T14:40:16.399932', '_rev': '6-3e0ede6e797af40860e9dadfb39056ce', 'last_modified': '2012-08-23T14:40:16.399932', 'biblio': {'title': 'Perceptual training strongly improves visual motion perception in schizophrenia', 'journal': 'Brain and Cognition', 'year': 2011, 'authors': u'Norton, McBain, \xd6ng\xfcr, Chen'}, '_id': '4mlln04q1rxy6l9oeb3t7ftv', 'type': 'item', 'aliases': {'url': ['http://linkinghub.elsevier.com/retrieve/pii/S0278262611001308', 'http://www.ncbi.nlm.nih.gov/pubmed/21872380'], 'pmid': ['21872380'], 'doi': ['10.1016/j.bandc.2011.08.003'], 'title': ['Perceptual training strongly improves visual motion perception in schizophrenia']}}
        metrics_method_response = (2, 'http://api.mendeley.com/research/perceptual-training-strongly-improves-visual-motion-perception-schizophrenia/')
        response = item_module.add_metrics_data("mendeley:readers", metrics_method_response, item)
        print response

        expected = {'metrics': {'mendeley:groups': {'provenance_url': 'http://api.mendeley.com/research/perceptual-training-strongly-improves-visual-motion-perception-schizophrenia/', 
                                                    "values": {'raw': 2, 'raw_history': {'2012-08-23T21:41:05.526046': 2}}}}, 
            'last_modified': '2012-08-23T14:40:16.399932', 
            'created': '2012-08-23T14:40:16.399932', 
            'aliases': {'url': ['http://linkinghub.elsevier.com/retrieve/pii/S0278262611001308', 'http://www.ncbi.nlm.nih.gov/pubmed/21872380'], 'pmid': ['21872380'], 'doi': ['10.1016/j.bandc.2011.08.003'], 'title': ['Perceptual training strongly improves visual motion perception in schizophrenia']}, 
            '_id': '4mlln04q1rxy6l9oeb3t7ftv', '_rev': '6-3e0ede6e797af40860e9dadfb39056ce', 
            'biblio': {'authors': u'Norton, McBain, \xd6ng\xfcr, Chen', 'journal': 'Brain and Cognition', 'year': 2011, 'title': 'Perceptual training strongly improves visual motion perception in schizophrenia'}, 
            'type': 'item'}
        assert_equals(response, expected)

    def test_is_currently_updating_unknown(self):
        response = item_module.is_currently_updating("tiidnotinredis", self.r)
        assert_equals(response, False)

    def test_is_currently_updating_yes(self):
        self.r.set_num_providers_left("tiidthatisnotdone", 10)
        response = item_module.is_currently_updating("tiidthatisnotdone", self.r)
        assert_equals(response, True)

    def test_is_currently_updating_no(self):
        self.r.set_num_providers_left("tiidthatisnotdone", 0)        
        response = item_module.is_currently_updating("tiidthatisdone", self.r)
        assert_equals(response, False)

    def test_clean_for_export_no_key(self):
        self.TEST_OBJECT = item_module.create_objects_from_item_doc(self.ITEM_DATA)        
        self.db.session.add(self.TEST_OBJECT)
        self.db.session.commit()

        item = item_module.get_item("test", self.myrefsets, self.d)
        item["metrics"]["scopus:citations"] = {"values":{"raw": 22}}
        item["metrics"]["citeulike:bookmarks"] = {"values":{"raw": 33}}
        response = item_module.clean_for_export(item)
        print response["metrics"].keys()
        expected = ['topsy:tweets', 'wikipedia:mentions']
        assert_equals(response["metrics"].keys(), expected)

    def test_clean_for_export_given_correct_secret_key(self):
        self.TEST_OBJECT = item_module.create_objects_from_item_doc(self.ITEM_DATA)        
        self.db.session.add(self.TEST_OBJECT)
        self.db.session.commit()

        item = item_module.get_item("test", self.myrefsets, self.d)
        item["metrics"]["scopus:citations"] = {"values":{"raw": 22}}
        item["metrics"]["citeulike:bookmarks"] = {"values":{"raw": 33}}
        response = item_module.clean_for_export(item, "SECRET", "SECRET")
        print response["metrics"].keys()
        expected = ['topsy:tweets', 'wikipedia:mentions', 'scopus:citations', 'citeulike:bookmarks']
        assert_equals(sorted(response["metrics"].keys()), sorted(expected))

    def test_clean_for_export_given_wrong_secret_key(self):
        self.TEST_OBJECT = item_module.create_objects_from_item_doc(self.ITEM_DATA)        
        self.db.session.add(self.TEST_OBJECT)
        self.db.session.commit()

        item = item_module.get_item("test", self.myrefsets, self.d)
        item["metrics"]["scopus:citations"] = {"values":{"raw": 22}}
        item["metrics"]["citeulike:bookmarks"] = {"values":{"raw": 33}}
        response = item_module.clean_for_export(item, "WRONG", "SECRET")
        print response["metrics"].keys()
        expected = ['topsy:tweets', 'wikipedia:mentions']
        assert_equals(response["metrics"].keys(), expected)



