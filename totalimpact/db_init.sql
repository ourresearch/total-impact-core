CREATE TABLE email (
        id text NOT NULL,
        created timestamptz,
        payload text NOT NULL,
        PRIMARY KEY (id));

CREATE TABLE api_users (
        api_key text NOT NULL,
        created timestamptz,
        planned_use text,
        example_url text,
        api_key_owner text,
        notes text,
        email text,
        organization text,
        max_registered_items numeric,
        PRIMARY KEY (api_key));

CREATE TABLE registered_items (
        api_key text NOT NULL,
        alias text NOT NULL,
        registered_date timestamptz,
        PRIMARY KEY (api_key, alias));