from sqlalchemy.exc import OperationalError

def slow(f):
    f.slow = True
    return f

def http(f):
    f.http = True
    return f

def setup_postgres_for_unittests(db, app):
    if not "localhost" in app.config["SQLALCHEMY_DATABASE_URI"]:
        assert(False), "Not running this unittest because SQLALCHEMY_DATABASE_URI is not on localhost"

    try:
        db.drop_all()
    except OperationalError, e:  #database "database" does not exist
        print e
        pass
    db.create_all()
    return db


def teardown_postgres_for_unittests(db):
    db.session.close_all()
