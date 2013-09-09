from totalimpact import db, app
from totalimpact import incoming_email
from totalimpact.incoming_email import IncomingEmail

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import OperationalError

import os, json, copy

from nose.tools import raises, assert_equals, nottest
import unittest
from test.utils import setup_postgres_for_unittests, teardown_postgres_for_unittests


class TestIncomingEmail():

    def setUp(self):
        self.db = setup_postgres_for_unittests(db, app)

        # example from http://docs.cloudmailin.com/http_post_formats/json/        
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

    def tearDown(self):
        teardown_postgres_for_unittests(self.db)



    def test_init_incoming_mail(self):
        all_email = IncomingEmail.query.all()
        assert_equals(all_email, [])

        self.existing_email = IncomingEmail(self.example_payload)

        self.db.session.add(self.existing_email)
        self.db.session.commit()

        all_email = IncomingEmail.query.all()
        assert_equals(len(all_email), 1)
        assert_equals(json.loads(all_email[0].payload), self.example_payload)

    def test_save_email(self):
        all_email = IncomingEmail.query.all()
        assert_equals(all_email, [])

        #does the commits etc
        self.existing_email = incoming_email.save_incoming_email(self.example_payload)

        all_email = IncomingEmail.query.all()
        assert_equals(len(all_email), 1)
        assert_equals(json.loads(all_email[0].payload), self.example_payload)


    def test_log_if_google_scholar_notification_confirmation(self):
        self.confirmation_email = IncomingEmail(self.example_payload)
        response = self.confirmation_email.log_if_google_scholar_notification_confirmation()
        print response
        expected = ('Jonathan A. Eisen', 'http://scholar.google.ca/scholar_alerts?update_op=confirm_alert&hl=en&alert_id=IMEzMffmofYJ&email_for_op=7be5eb5001593217143f%40cloudmailin.net')
        assert_equals(response, expected)

        self.example_payload["plain"] = "this is not the email you are looking for"
        different_email = IncomingEmail(self.example_payload)
        response = different_email.log_if_google_scholar_notification_confirmation()
        expected = (None, None)
        assert_equals(response, expected)


    def test_log_if_google_scholar_new_articles(self):
        self.example_payload["headers"]["Subject"] = "Scholar Alert - John P. A. Ioannidis - new articles"
        self.new_articles_email = IncomingEmail(self.example_payload)
        response = self.new_articles_email.log_if_google_scholar_new_articles()
        expected = 'John P. A. Ioannidis'
        assert_equals(response, expected)

        self.example_payload["headers"]["Subject"] = "this is not the email you are looking for"
        different_email = IncomingEmail(self.example_payload)
        response = different_email.log_if_google_scholar_new_articles()
        expected = None
        assert_equals(response, expected)




