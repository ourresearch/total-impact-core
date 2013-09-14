import datetime, json, re
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import FlushError
from totalimpact import db

import logging
logger = logging.getLogger('ti.incoming_email')

def save_incoming_email(payload):
    email = IncomingEmail(payload)
    email.log_if_google_scholar_notification_confirmation()
    email.log_if_google_scholar_new_articles()

    db.session.add(email)
    try:
        db.session.commit()
    except (IntegrityError, FlushError) as e:
        db.session.rollback()
        logger.warning(u"Fails Integrity check in add_items_to_collection_object for {cid}, rolling back.  Message: {message}".format(
            cid=cid, 
            message=e.message))        

    return email


class IncomingEmail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime())
    payload = db.Column(db.Text)

    def __init__(self, payload):
        self.payload = json.dumps(payload)
        self.created = datetime.datetime.utcnow()
        super(IncomingEmail, self).__init__()

    @property
    def subject(self):
        payload = json.loads(self.payload)
        return payload["headers"]["Subject"]

    @property
    def email_body(self):
        payload = json.loads(self.payload)
        return payload["plain"]

    def __repr__(self):
        return '<IncomingEmail {id}, {created}, {payload_start}>'.format(
            id=self.id, 
            created=self.created, 
            payload_start=self.payload[0:100])

    def log_if_google_scholar_notification_confirmation(self):
        GOOGLE_SCHOLAR_CONFIRM_PATTERN = re.compile("""for the query:\nNew articles in (?P<name>.*)'s profile\n\nClick to confirm this request:\n(?P<url>.*)\n\n""")
        name = None
        url = None
        try:
            match = GOOGLE_SCHOLAR_CONFIRM_PATTERN.search(self.email_body)
            if match:
                url = match.group("url")
                name = match.group("name")
                logger.info(u"Google Scholar notification confirmation for {name} is at {url}".format(
                    name=name, url=url))
        except (KeyError, TypeError):
            pass
        return(name, url)

    def log_if_google_scholar_new_articles(self):
        GOOGLE_SCHOLAR_NEW_ARTICLES_PATTERN = re.compile("""Scholar Alert - (?P<name>.*) - new articles""")
        name = None
        try:
            match = GOOGLE_SCHOLAR_NEW_ARTICLES_PATTERN.search(self.subject)
            if match:
                name = match.group("name")
                logger.info(u"Just received Google Scholar alert: new articles for {name}, saved at {id}".format(
                    name=name, 
                    id=self.id))
        except (KeyError, TypeError):
            pass
        return(name)

