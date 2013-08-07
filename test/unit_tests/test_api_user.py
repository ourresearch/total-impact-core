from totalimpact import api_user, tiredis
import os, json

from nose.tools import raises, assert_equals, nottest
import unittest


class TestApiUser():

    def setUp(self):
        from totalimpact import dao

        # hacky way to delete the "ti" db, then make it fresh again for each test.
        temp_dao = dao.Dao("http://localhost:5984", os.getenv("CLOUDANT_DB"))
        temp_dao.delete_db(os.getenv("CLOUDANT_DB"))
        self.d = dao.Dao("http://localhost:5984", os.getenv("CLOUDANT_DB"))
        self.d.update_design_doc()

        #postgres
        self.postgres_d = dao.PostgresDao("postgres://localhost/unittests")
        self.postgres_d.create_tables()

        # setup a clean new redis test database.  We're putting unittest redis at DB Number 8.
        self.r = tiredis.from_url("redis://localhost:6379", db=8)
        self.r.flushdb()

        self.test_alias = ("doi", "10.1371/journal.pcbi.1")
        self.test_alias_registered = ("doi", "10.1371/journal.pcbi.2")
        self.test_alias_registered_string = ":".join(self.test_alias_registered)

        cur = self.postgres_d.get_cursor()
        cur.execute("truncate table api_users;")
        cur.execute("truncate table registered_items;")
        cur.execute("insert into api_users (api_key, max_registered_items) values ('SFUlqzam8', 3);")
        cur.execute("insert into registered_items (api_key, alias) values ('SFUlqzam8', 'doi:10.1371/journal.pcbi.2')")
        cur.close()

    def tearDown(self):
        self.postgres_d.close()

    def test_save_api_user(self):
        api_key_prefix = "SFU"
        meta = {'usage': 'individual CV', 'email': '', 'notes': '', 'api_limit': '', 'api_key_owner': '', 'planned_use':'', "example_url":"", "organization":""}
        new_api_key = api_user.save_api_user(api_key_prefix, 1000, self.postgres_d, **meta)
        print new_api_key

        cur = self.postgres_d.get_cursor()
        cur.execute("""SELECT * FROM api_users 
                WHERE api_key=%s""", 
                (new_api_key,))
        response = cur.fetchall()
        cur.close()
        assert_equals(len(response), 1)

        response = api_user.get_api_user_id_by_api_key(new_api_key, self.postgres_d)
        assert_equals(response, new_api_key.lower())

    def test_get_api_user_id_by_api_key(self):
        api_key = "SFUlqzam8"
        response = api_user.get_api_user_id_by_api_key(api_key, self.postgres_d)
        assert_equals(response, api_key.lower())

        response = api_user.get_api_user_id_by_api_key("NOTVALIDKEY", self.postgres_d)
        assert_equals(response, None)

    def test_is_registered(self):
        response = api_user.is_registered(self.test_alias, "SFUlqzam8", self.postgres_d)
        assert_equals(response, False)

        response = api_user.is_registered(self.test_alias_registered, "SFUlqzam8", self.postgres_d)
        assert_equals(response, True)

    @raises(api_user.InvalidApiKeyException)
    def test_register_item_invalid_key(self):
        api_user.register_item(self.test_alias, "INVALID_KEY", self.r, self.d, self.postgres_d)

    def test_is_over_quota(self):
        api_key = "SFUlqzam8"
        response = api_user.is_over_quota(api_key, self.postgres_d)
        assert_equals(response, False)

        api_user.add_registration_data(("doi", "10.a"), api_key, self.postgres_d)
        api_user.add_registration_data(("doi", "10.b"), api_key, self.postgres_d)
        api_user.add_registration_data(("doi", "10.c"), api_key, self.postgres_d)
        response = api_user.is_over_quota(api_key, self.postgres_d)
        assert_equals(response, True)

    def test_register_item_success(self):
        api_key = "SFUlqzam8"
        response = api_user.is_registered(self.test_alias, api_key, self.postgres_d)
        assert_equals(response, False)

        api_user.register_item(self.test_alias, api_key, self.r, self.d, self.postgres_d)
        response = api_user.is_registered(self.test_alias, api_key, self.postgres_d)
        assert_equals(response, True)



