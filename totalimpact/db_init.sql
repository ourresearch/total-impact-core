CREATE TABLE email (
        id text NOT NULL,
        created timestamptz,
        payload text NOT NULL,
        PRIMARY KEY (id));

