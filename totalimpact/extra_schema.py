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

create_view_min_biblio()    