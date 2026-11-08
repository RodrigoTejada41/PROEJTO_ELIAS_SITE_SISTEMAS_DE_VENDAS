BEGIN;

CREATE TABLE inventory_policy (
    id boolean PRIMARY KEY DEFAULT true CHECK (id),
    allow_negative boolean NOT NULL DEFAULT false,
    workbook_key uuid NOT NULL DEFAULT gen_random_uuid()
);
INSERT INTO inventory_policy DEFAULT VALUES;

CREATE TABLE inventory_policy_audit (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_id bigint NOT NULL REFERENCES identity_users (id),
    allow_negative boolean NOT NULL,
    occurred_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE inventory_entry_batches (
    id uuid PRIMARY KEY,
    actor_id bigint NOT NULL REFERENCES identity_users (id),
    fingerprint text NOT NULL,
    result jsonb NOT NULL,
    occurred_at timestamptz NOT NULL DEFAULT now()
);

ALTER VIEW administrative_audit RENAME TO administrative_audit_before_inventory_policy;
CREATE VIEW administrative_audit AS
SELECT * FROM administrative_audit_before_inventory_policy
UNION ALL
SELECT 'inventory_policy', a.id, a.occurred_at,
       CASE WHEN a.allow_negative THEN 'stock_negative_enabled' ELSE 'stock_negative_disabled' END,
       actor.username, 'inventory_policy', 1::bigint
FROM inventory_policy_audit a JOIN identity_users actor ON actor.id = a.actor_id;

COMMIT;
