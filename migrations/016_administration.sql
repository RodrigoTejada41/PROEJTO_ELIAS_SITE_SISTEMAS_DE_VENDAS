BEGIN;

ALTER TABLE identity_users DROP CONSTRAINT identity_users_role_check;
ALTER TABLE identity_users ADD CONSTRAINT identity_users_role_check
    CHECK (role IN ('DEV', 'MASTER', 'OPERATOR'));
CREATE UNIQUE INDEX identity_single_dev ON identity_users (role) WHERE role = 'DEV';

CREATE TABLE company_profile (
    id smallint PRIMARY KEY CHECK (id = 1),
    name varchar(160) NOT NULL CHECK (btrim(name) <> ''),
    trade_name varchar(160) NOT NULL,
    tax_id varchar(32) NOT NULL,
    address varchar(240) NOT NULL,
    phone varchar(48) NOT NULL
);

CREATE TABLE company_audit (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_id bigint NOT NULL REFERENCES identity_users (id),
    occurred_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE sale_receipts (
    sale_id bigint PRIMARY KEY REFERENCES sales (id),
    company_snapshot jsonb NOT NULL
);

ALTER VIEW administrative_audit RENAME TO administrative_audit_previous;
CREATE VIEW administrative_audit AS
SELECT * FROM administrative_audit_previous
UNION ALL
SELECT 'company', a.id, a.occurred_at, 'company_updated', actor.username, 'company', 1::bigint
FROM company_audit a JOIN identity_users actor ON actor.id = a.actor_id;

COMMIT;
