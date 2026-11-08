BEGIN;

CREATE TABLE catalog_skus (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code varchar(64) NOT NULL UNIQUE CHECK (code COLLATE "C" ~ '^[A-Z0-9._-]+$'),
    description varchar(160) NOT NULL CHECK (description <> '' AND description = btrim(description)),
    brand varchar(100),
    category varchar(100),
    variation varchar(100),
    barcode varchar(32) UNIQUE CHECK (barcode COLLATE "C" ~ '^[0-9]+$'),
    active boolean NOT NULL DEFAULT true,
    version bigint NOT NULL DEFAULT 1 CHECK (version > 0)
);

CREATE TABLE catalog_audit (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sku_id bigint NOT NULL REFERENCES catalog_skus (id),
    actor_id bigint NOT NULL REFERENCES identity_users (id),
    action text NOT NULL CHECK (action IN ('created', 'edited', 'deactivated')),
    occurred_at timestamptz NOT NULL DEFAULT now()
);

COMMIT;
