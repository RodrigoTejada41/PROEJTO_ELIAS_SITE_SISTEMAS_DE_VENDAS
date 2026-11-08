BEGIN;

CREATE TABLE finance_settings (
    id boolean PRIMARY KEY DEFAULT true CHECK (id),
    currency varchar(3) NOT NULL CHECK (currency COLLATE "C" ~ '^[A-Z]{3}$'),
    scale smallint NOT NULL CHECK (scale BETWEEN 0 AND 4)
);

CREATE TABLE finance_titles (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kind text NOT NULL CHECK (kind IN ('receivable', 'payable')),
    party_id bigint REFERENCES commercial_parties (id),
    description varchar(160) NOT NULL CHECK (char_length(btrim(description)) BETWEEN 1 AND 160),
    amount_minor bigint NOT NULL CHECK (amount_minor BETWEEN 1 AND 999999999999),
    currency varchar(3) NOT NULL,
    scale smallint NOT NULL CHECK (scale BETWEEN 0 AND 4),
    due_date date NOT NULL,
    actor_id bigint NOT NULL REFERENCES identity_users (id),
    request_key uuid NOT NULL UNIQUE,
    canceled boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE finance_settlements (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title_id bigint NOT NULL REFERENCES finance_titles (id),
    actor_id bigint NOT NULL REFERENCES identity_users (id),
    amount_minor bigint NOT NULL CHECK (amount_minor BETWEEN 1 AND 999999999999),
    method text NOT NULL CHECK (method IN ('cash', 'transfer', 'card', 'other')),
    request_key uuid NOT NULL UNIQUE,
    occurred_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX finance_settlement_title ON finance_settlements (title_id);

CREATE TABLE finance_reversals (
    settlement_id bigint PRIMARY KEY REFERENCES finance_settlements (id),
    actor_id bigint NOT NULL REFERENCES identity_users (id),
    reason varchar(240) NOT NULL CHECK (char_length(btrim(reason)) BETWEEN 3 AND 240),
    request_key uuid NOT NULL UNIQUE,
    occurred_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE finance_audit (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title_id bigint REFERENCES finance_titles (id),
    actor_id bigint NOT NULL REFERENCES identity_users (id),
    action text NOT NULL CHECK (action IN ('configured', 'created', 'settled', 'reversed', 'canceled')),
    occurred_at timestamptz NOT NULL DEFAULT now()
);

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
FROM finance_audit a JOIN identity_users actor ON actor.id = a.actor_id;

COMMIT;
