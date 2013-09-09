from totalimpact import db, app
from totalimpact import provider_batch_data
from totalimpact.provider_batch_data import ProviderBatchData

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import OperationalError

import os, json, copy

from nose.tools import raises, assert_equals, nottest
import unittest
from test.utils import setup_postgres_for_unittests, teardown_postgres_for_unittests


class TestProviderBatchData():

    def setUp(self):
        self.db = setup_postgres_for_unittests(db, app)

        self.test_data = {
               "raw": "<pmc-web-stat><request year=\"2012\" month=\"10\" jrid=\"elife\" eissn=\"2050-084X\"></request><response status=\"0\" collection=\"eLife\"></response><articles><article id=\"PMC3463246\"><meta-data doi=\"10.7554/eLife.00013\" pmcid=\"PMC3463246\" pubmed-id=\"23066504\" pub-year=\"2012\" volume=\"1\" issue=\"\" first-page=\"e00013\"/><usage unique-ip=\"1368\" full-text=\"1464\" pdf=\"722\" abstract=\"119\" scanned-summary=\"0\" scanned-page-browse=\"0\" figure=\"144\" supp-data=\"0\" cited-by=\"0\"/></article><article id=\"PMC3463247\"><meta-data doi=\"10.7554/eLife.00240\" pmcid=\"PMC3463247\" pubmed-id=\"23066507\" pub-year=\"2012\" volume=\"1\" issue=\"\" first-page=\"e00240\"/><usage unique-ip=\"514\" full-text=\"606\" pdf=\"230\" abstract=\"0\" scanned-summary=\"0\" scanned-page-browse=\"0\" figure=\"9\" supp-data=\"0\" cited-by=\"0\"/></article><article id=\"PMC3465569\"><meta-data doi=\"10.7554/eLife.00242\" pmcid=\"PMC3465569\" pubmed-id=\"23066508\" pub-year=\"2012\" volume=\"1\" issue=\"\" first-page=\"e00242\"/><usage unique-ip=\"473\" full-text=\"503\" pdf=\"181\" abstract=\"2\" scanned-summary=\"0\" scanned-page-browse=\"0\" figure=\"13\" supp-data=\"0\" cited-by=\"0\"/></article><article id=\"PMC3465570\"><meta-data doi=\"10.7554/eLife.00243\" pmcid=\"PMC3465570\" pubmed-id=\"23066509\" pub-year=\"2012\" volume=\"1\" issue=\"\" first-page=\"e00243\"/><usage unique-ip=\"547\" full-text=\"636\" pdf=\"227\" abstract=\"1\" scanned-summary=\"0\" scanned-page-browse=\"0\" figure=\"56\" supp-data=\"0\" cited-by=\"0\"/></article><article id=\"PMC3466591\"><meta-data doi=\"10.7554/eLife.00065\" pmcid=\"PMC3466591\" pubmed-id=\"23066506\" pub-year=\"2012\" volume=\"1\" issue=\"\" first-page=\"e00065\"/><usage unique-ip=\"2516\" full-text=\"2804\" pdf=\"1583\" abstract=\"195\" scanned-summary=\"0\" scanned-page-browse=\"0\" figure=\"405\" supp-data=\"0\" cited-by=\"0\"/></article><article id=\"PMC3466783\"><meta-data doi=\"10.7554/eLife.00007\" pmcid=\"PMC3466783\" pubmed-id=\"23066503\" pub-year=\"2012\" volume=\"1\" issue=\"\" first-page=\"e00007\"/><usage unique-ip=\"1331\" full-text=\"1412\" pdf=\"898\" abstract=\"224\" scanned-summary=\"0\" scanned-page-browse=\"0\" figure=\"109\" supp-data=\"0\" cited-by=\"0\"/></article><article id=\"PMC3467772\"><meta-data doi=\"10.7554/eLife.00270\" pmcid=\"PMC3467772\" pubmed-id=\"23066510\" pub-year=\"2012\" volume=\"1\" issue=\"\" first-page=\"e00270\"/><usage unique-ip=\"1396\" full-text=\"1776\" pdf=\"625\" abstract=\"4\" scanned-summary=\"0\" scanned-page-browse=\"0\" figure=\"0\" supp-data=\"0\" cited-by=\"0\"/></article><article id=\"PMC3470722\"><meta-data doi=\"10.7554/eLife.00286\" pmcid=\"PMC3470722\" pubmed-id=\"23071903\" pub-year=\"2012\" volume=\"1\" issue=\"\" first-page=\"e00286\"/><usage unique-ip=\"909\" full-text=\"1030\" pdf=\"376\" abstract=\"6\" scanned-summary=\"0\" scanned-page-browse=\"0\" figure=\"0\" supp-data=\"0\" cited-by=\"0\"/></article><article id=\"PMC3479833\"><meta-data doi=\"10.7554/eLife.00031\" pmcid=\"PMC3479833\" pubmed-id=\"23110253\" pub-year=\"2012\" volume=\"1\" issue=\"\" first-page=\"e00031\"/><usage unique-ip=\"154\" full-text=\"126\" pdf=\"87\" abstract=\"26\" scanned-summary=\"0\" scanned-page-browse=\"0\" figure=\"13\" supp-data=\"0\" cited-by=\"0\"/></article><article id=\"PMC3470409\"><meta-data doi=\"10.7554/eLife.00048\" pmcid=\"PMC3470409\" pubmed-id=\"23066505\" pub-year=\"2012\" volume=\"1\" issue=\"\" first-page=\"e00048\"/><usage unique-ip=\"1250\" full-text=\"1361\" pdf=\"911\" abstract=\"237\" scanned-summary=\"0\" scanned-page-browse=\"0\" figure=\"317\" supp-data=\"4\" cited-by=\"0\"/></article><article id=\"PMC3482692\"><meta-data doi=\"10.7554/eLife.00102\" pmcid=\"PMC3482692\" pubmed-id=\"23110254\" pub-year=\"2012\" volume=\"1\" issue=\"\" first-page=\"e00102\"/><usage unique-ip=\"259\" full-text=\"232\" pdf=\"133\" abstract=\"36\" scanned-summary=\"0\" scanned-page-browse=\"0\" figure=\"8\" supp-data=\"3\" cited-by=\"0\"/></article><article id=\"PMC3482687\"><meta-data doi=\"10.7554/eLife.00281\" pmcid=\"PMC3482687\" pubmed-id=\"23110255\" pub-year=\"2012\" volume=\"1\" issue=\"\" first-page=\"e00281\"/><usage unique-ip=\"75\" full-text=\"53\" pdf=\"47\" abstract=\"0\" scanned-summary=\"0\" scanned-page-browse=\"0\" figure=\"1\" supp-data=\"0\" cited-by=\"0\"/></article><article id=\"PMC3482686\"><meta-data doi=\"10.7554/eLife.00005\" pmcid=\"PMC3482686\" pubmed-id=\"23110252\" pub-year=\"2012\" volume=\"1\" issue=\"\" first-page=\"e00005\"/><usage unique-ip=\"324\" full-text=\"249\" pdf=\"263\" abstract=\"71\" scanned-summary=\"0\" scanned-page-browse=\"0\" figure=\"93\" supp-data=\"17\" cited-by=\"0\"/></article></articles></pmc-web-stat>",
               "max_event_date": "2012-10-31T07:34:01.126892",
               "provider": "pmc",
               "aliases": {
                   "pmid": [
                       "23066504",
                       "23066507",
                       "23066508",
                       "23066509",
                       "23066506",
                       "23066503",
                       "23066510",
                       "23071903",
                       "23110253",
                       "23066505",
                       "23110254",
                       "23110255",
                       "23110252"
                   ]
               },
               "provider_raw_version": 1,
               "min_event_date": "2012-10-01T07:34:01.126892",
               "created": "2012-11-29T07:34:01.126892"
            }        

    def tearDown(self):
        teardown_postgres_for_unittests(self.db)


    def test_make_provider_batch_data(self):
        #make sure nothing there beforehand
        matching = ProviderBatchData.query.filter_by(provider="pmc").first()
        assert_equals(matching, None)

        new_batch_data = ProviderBatchData(**self.test_data)
        print new_batch_data

        # still not there
        matching = ProviderBatchData.query.filter_by(provider="pmc").first()
        assert_equals(matching, None)

        self.db.session.add(new_batch_data)
        self.db.session.commit()

        # and now poof there it is
        matching = ProviderBatchData.query.filter_by(provider="pmc").first()
        assert_equals(matching.provider, "pmc")

        assert_equals(json.loads(matching.aliases), self.test_data["aliases"])



