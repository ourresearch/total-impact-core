from sqlalchemy.exc import OperationalError

def slow(f):
    f.slow = True
    return f

def http(f):
    f.http = True
    return f

# from http://www.sqlalchemy.org/trac/wiki/UsageRecipes/DropEverything
# with a few changes

def drop_everything(db, app):
    from sqlalchemy.engine import reflection
    from sqlalchemy import create_engine
    from sqlalchemy.schema import (
        MetaData,
        Table,
        DropTable,
        ForeignKeyConstraint,
        DropConstraint,
        )

    conn = db.session()

    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    inspector = reflection.Inspector.from_engine(engine)

    # gather all data first before dropping anything.
    # some DBs lock after things have been dropped in 
    # a transaction.
    
    metadata = MetaData()

    tbs = []
    all_fks = []

    for table_name in inspector.get_table_names():
        fks = []
        for fk in inspector.get_foreign_keys(table_name):
            if not fk['name']:
                continue
            fks.append(
                ForeignKeyConstraint((),(),name=fk['name'])
                )
        t = Table(table_name,metadata,*fks)
        tbs.append(t)
        all_fks.extend(fks)

    conn.execute("""drop view if exists min_biblio""")

    for fkc in all_fks:
        conn.execute(DropConstraint(fkc))

    for table in tbs:
        conn.execute(DropTable(table))

    db.session.commit()    


def setup_postgres_for_unittests(db, app):
    if not "localhost" in app.config["SQLALCHEMY_DATABASE_URI"]:
        assert(False), "Not running this unittest because SQLALCHEMY_DATABASE_URI is not on localhost"

    drop_everything(db, app)
    db.create_all()

    from totalimpact import extra_schema 
    extra_schema.create_view_min_biblio()

    return db


def teardown_postgres_for_unittests(db):
    db.session.close_all()
