from totalimpact import views, db

def create_view_min_biblio():
    result = db.session.execute("""create or replace view min_biblio as (
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
    db.session.commit()


def create_doaj_table():
    doaj_setup_sql = """
        CREATE TABLE if not exists doaj (
            title varchar(250),
            publisher varchar(250),
            issn varchar(25) NOT NULL,
            eissn varchar(25),
            "cc license" varchar(25),
            PRIMARY KEY (issn)
        );"""    
    result = db.session.execute(doaj_setup_sql)
    db.session.commit()

def create_doaj_view():
    doaj_setup_sql = """
        CREATE or replace VIEW doaj_issn_lookup (issn) AS          
            SELECT replace((doaj.issn)::text, '-'::text, ''::text) AS issn FROM doaj
                UNION
            SELECT replace((doaj.eissn)::text, '-'::text, ''::text) AS issn FROM doaj;
        """    
    result = db.session.execute(doaj_setup_sql)
    db.session.commit()

create_view_min_biblio()    
create_doaj_table()    
create_doaj_view()    