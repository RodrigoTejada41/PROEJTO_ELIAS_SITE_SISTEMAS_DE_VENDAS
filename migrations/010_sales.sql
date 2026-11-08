BEGIN;

CREATE TABLE sales (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'confirmed', 'canceled')),
    customer_id bigint REFERENCES commercial_parties (id),
    seller_id bigint NOT NULL REFERENCES identity_users (id),
    actor_id bigint NOT NULL REFERENCES identity_users (id),
    currency varchar(3) NOT NULL,
    scale smallint NOT NULL CHECK (scale BETWEEN 0 AND 4),
    discount_minor bigint NOT NULL DEFAULT 0 CHECK (discount_minor BETWEEN 0 AND 999999999999),
    due_date date NOT NULL,
    version bigint NOT NULL DEFAULT 1 CHECK (version > 0),
    request_key uuid NOT NULL UNIQUE,
    customer_name varchar(160),
    seller_name varchar(64) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    confirmed_at timestamptz,
    canceled_at timestamptz
);

CREATE TABLE sale_items (
    sale_id bigint NOT NULL REFERENCES sales (id),
    sku_id bigint NOT NULL REFERENCES catalog_skus (id),
    code_snapshot varchar(64) NOT NULL,
    description_snapshot varchar(160) NOT NULL,
    quantity bigint NOT NULL CHECK (quantity BETWEEN 1 AND 1000000000),
    unit_minor bigint NOT NULL CHECK (unit_minor BETWEEN 1 AND 999999999999),
    PRIMARY KEY (sale_id, sku_id)
);

CREATE TABLE sale_audit (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sale_id bigint NOT NULL REFERENCES sales (id),
    actor_id bigint NOT NULL REFERENCES identity_users (id),
    action text NOT NULL,
    occurred_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE finance_titles ADD COLUMN sale_id bigint UNIQUE REFERENCES sales (id);
ALTER TABLE inventory_movements ADD COLUMN sale_id bigint REFERENCES sales (id);

ALTER TABLE commercial_parties ADD CONSTRAINT commercial_ref_format
    CHECK (external_ref COLLATE "C" ~ '^[A-Z0-9._/-]+$');

CREATE OR REPLACE VIEW administrative_audit AS
SELECT 'identity'::text AS source, a.id, a.occurred_at, a.event AS action,
       coalesce(actor.username, a.actor_db_role::text, target.username) AS actor,
       'user'::text AS entity, a.user_id AS target_id
FROM identity_audit a JOIN identity_users target ON target.id = a.user_id
LEFT JOIN identity_users actor ON actor.id = a.actor_user_id
UNION ALL
SELECT 'catalog', a.id, a.occurred_at, a.action, actor.username, 'sku', a.sku_id
FROM catalog_audit a JOIN identity_users actor ON actor.id = a.actor_id
UNION ALL
SELECT 'inventory', m.id, m.occurred_at,
       CASE WHEN m.compensates_id IS NOT NULL THEN 'compensation' WHEN m.delta > 0 THEN 'entry' ELSE 'exit' END,
       actor.username, 'sku', m.sku_id
FROM inventory_movements m JOIN identity_users actor ON actor.id = m.actor_id
UNION ALL
SELECT 'contacts', a.id, a.occurred_at, a.action, actor.username, party.kind, a.party_id
FROM commercial_party_audit a JOIN identity_users actor ON actor.id = a.actor_id
JOIN commercial_parties party ON party.id = a.party_id
UNION ALL
SELECT 'finance', a.id, a.occurred_at, a.action, actor.username, 'title', a.title_id
FROM finance_audit a JOIN identity_users actor ON actor.id = a.actor_id
UNION ALL
SELECT 'sales', a.id, a.occurred_at, a.action, actor.username, 'sale', a.sale_id
FROM sale_audit a JOIN identity_users actor ON actor.id = a.actor_id;

COMMIT;
