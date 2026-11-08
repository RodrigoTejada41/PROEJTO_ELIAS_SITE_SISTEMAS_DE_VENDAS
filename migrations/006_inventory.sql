BEGIN;

CREATE TABLE inventory_movements (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sku_id bigint NOT NULL REFERENCES catalog_skus (id),
    actor_id bigint NOT NULL REFERENCES identity_users (id),
    delta bigint NOT NULL CHECK (delta <> 0 AND abs(delta) <= 1000000000),
    reason varchar(240) NOT NULL CHECK (char_length(btrim(reason)) BETWEEN 3 AND 240),
    request_key uuid NOT NULL UNIQUE,
    compensates_id bigint UNIQUE REFERENCES inventory_movements (id),
    occurred_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX inventory_sku_history ON inventory_movements (sku_id, id DESC);

COMMIT;
