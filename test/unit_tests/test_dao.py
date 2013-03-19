import os, datetime, json
import unittest, nose.tools
from nose.tools import nottest, raises, assert_equals, assert_true
from totalimpact import dao

TEST_DB_NAME = "test_dao"


class TestDbUrl(unittest.TestCase):
    
    def setUp(self):
        url = "https://mah_username:mah_password@mah_username.cloudant.com"
        self.db_url = dao.DbUrl(url)
        pass
    
    def test_get_username(self):
        username = self.db_url.get_username()
        assert_equals(
            username,
            "mah_username"
        )
    def test_get_password(self):
        password = self.db_url.get_password()
        assert_equals(
            password,
            "mah_password"
        )
    def test_get_base(self):
        base = self.db_url.get_base()
        assert_equals(
            base,
            "https://mah_username.cloudant.com"
        )
        

class TestDAO(unittest.TestCase):

    def setUp(self):
        # hacky way to delete the "ti" db, then make it fresh again for each test.
        temp_dao = dao.Dao("http://localhost:5984", os.getenv("CLOUDANT_DB"))
        temp_dao.delete_db(os.getenv("CLOUDANT_DB"))
        self.d = dao.Dao("http://localhost:5984", os.getenv("CLOUDANT_DB"))
        self.d.update_design_doc()

    def teardown(self):
        pass

    def test_create_db_uploads_views(self):
        design_doc = self.d.db.get("_design/queues")
        assert_equals(set(design_doc["views"].keys()),
            set([u'by_alias', "by_type_and_id", "latest-collections"]))

        design_doc = self.d.db.get("_design/collections_with_items")
        assert_equals(set(design_doc["views"].keys()),
            set([u"collections_with_items"]))

        design_doc = self.d.db.get("_design/reference-sets")
        assert_equals(set(design_doc["views"].keys()),
            set([u"reference-sets"]))

    def test_connect_db(self):
        assert self.d.db.__class__.__name__ == "Database"

    def test_delete(self):
        id = "123"

        ret = self.d.save({"_id":"123"})
        assert_equals(id, ret[0])

        del_worked = self.d.delete(id)
        assert_equals(del_worked, True)
        assert_equals(self.d.get(id), None)

class TestPostgresDao(unittest.TestCase):

    def setUp(self):
        # hacky way to delete the unittest db, then make it fresh again for each test.
        #temp_dao = dao.PostgresDao("localhost")
        #temp_dao.delete_db(os.getenv("POSTGRESQL_DB"))
        #temp_dao.close()
        self.postgres_d = dao.PostgresDao("localhost", os.getenv("POSTGRESQL_DB"))
        self.postgres_d.create_tables()

        self.example_payload = {
               "headers": {
                   "To": "7be5eb5001593217143f@cloudmailin.net",
                   "Mime-Version": "1.0",
                   "X-Received": "by 10.58.45.134 with SMTP id n6mr13476387vem.35.1361476813304; Thu, 21 Feb 2013 12:00:13 -0800 (PST)",
                   "Received": "by mail-vc0-f202.google.com with SMTP id m8so955261vcd.3 for <7be5eb5001593217143f@cloudmailin.net>; Thu, 21 Feb 2013 12:00:13 -0800",
                   "From": "Google Scholar Alerts <scholaralerts-noreply@google.com>",
                   "DKIM-Signature": "v=1; a=rsa-sha256; c=relaxed/relaxed; d=google.com; s=20120113; h=mime-version:x-received:message-id:date:subject:from:to :content-type; bh=74dhtWOnoX2dYtmZibjD2+Tp65AZ7UnVwRTR7Qwho/o=; b=Fabq5urMfTyUX0s3XgFhVx1pyZ+tW/n38Sm/3T5EXTWeG2k7C6mxbrv1DdmpNpl/a8 Sr70eG6St7oytXii5tg9TrwrlwhftpFZKkJQS8GMWswiEaBkOfnNkoRrN174jRYfBUuZ oKWJr49dxw9hV3uKYoSis0zL6R8P+7GXt1rtqblBELrfIJ3pKC7d7WS65i6hdM2kA+sY va9geqt1fFFN7098U7WELlM2JoXhS4fbIQTev/Z6cF89Sfs4888GXb7PIq0d1kfd6t7c kXK8bV6TkqSP4AxDm646Cv1TR9cfo6+9yCrkK8oW6ihAMzM0Lwobq22NLrRY2QK8494s WAuA==",
                   "Date": "Thu, 21 Feb 2013 20:00:13 +0000",
                   "Message-ID": "<089e0115f968d3b38604d6418577@google.com>",
                   "Content-Type": "text/plain; charset=ISO-8859-1; delsp=yes; format=flowed",
                   "Subject": "Confirm your Google Scholar Alert"
               },
               "reply_plain": None,
               "attachments": [
               ],
               "plain": "Google received a request to start sending Scholar Alerts to  \n7be5eb5001593217143f@cloudmailin.net for the query:\nNew articles in Jonathan A. Eisen's profile\n\nClick to confirm this request:\nhttp://scholar.google.ca/scholar_alerts?update_op=confirm_alert&hl=en&alert_id=IMEzMffmofYJ&email_for_op=7be5eb5001593217143f%40cloudmailin.net\n\nClick to cancel this request:\nhttp://scholar.google.ca/scholar_alerts?view_op=cancel_alert_options&hl=en&alert_id=IMEzMffmofYJ&email_for_op=7be5eb5001593217143f%40cloudmailin.net\n\nThanks,\nThe Google Scholar Team",
               "envelope": {
                   "to": "7be5eb5001593217143f@cloudmailin.net",
                   "helo_domain": "mail-vc0-f202.google.com",
                   "from": "3zXwmURUKAO4iSXebQhQbUhji-dehUfboWeeWbU.Sec@scholar-alerts.bounces.google.com",
                   "remote_ip": "209.85.220.202",
                   "spf": {
                       "domain": "scholar-alerts.bounces.google.com",
                       "result": "neutral"
                   }
               },
               "html": None
            }        

    def teardown(self):
        self.postgres_d.close()

    def test_connect_db(self):
        assert self.postgres_d.conn.__class__.__name__ == "connection"

    def test_save_email(self):
        # set up by deleting all other unittest emails
        cur = self.postgres_d.get_cursor()
        cur.execute("TRUNCATE table email")

        doc_id = "test"
        doc = {"_id":doc_id, 
                "created":datetime.datetime.now().isoformat(),
                "payload":self.example_payload}

        doc_id = self.postgres_d.save_email(doc)

        stored_email = self.postgres_d.get_email(doc_id)

        assert_equals(len(stored_email), 1)
        assert_equals(stored_email[0].keys(), ['payload', 'id', 'created'])
        assert_equals(stored_email[0]["id"], doc_id)
        assert_equals(json.loads(stored_email[0]["payload"]), self.example_payload)


             
