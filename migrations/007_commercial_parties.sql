BEGIN;

CREATE TABLE commercial_parties (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kind text NOT NULL CHECK (kind IN ('customers', 'suppliers')),
    name varchar(160) NOT NULL CHECK (name <> '' AND name = btrim(name)),
    external_ref varchar(64),
    contact varchar(160),
    phone varchar(40),
    email varchar(254),
    active boolean NOT NULL DEFAULT true,
    version bigint NOT NULL DEFAULT 1 CHECK (version > 0),
    UNIQUE (kind, external_ref)
);

CREATE INDEX commercial_party_listing ON commercial_parties (kind, name, id);

CREATE TABLE commercial_party_audit (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    party_id bigint NOT NULL REFERENCES commercial_parties (id),
    actor_id bigint NOT NULL REFERENCES identity_users (id),
    action text NOT NULL CHECK (action IN ('created', 'edited', 'deactivated')),
    occurred_at timestamptz NOT NULL DEFAULT now()
);

COMMIT;
