BEGIN;

CREATE TABLE commission_rules (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    seller_id bigint NOT NULL REFERENCES identity_users (id),
    percent numeric(7,4) NOT NULL CHECK (percent BETWEEN 0 AND 100),
    event text NOT NULL CHECK (event IN ('confirmed', 'received')),
    actor_id bigint NOT NULL REFERENCES identity_users (id),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX commission_rule_seller ON commission_rules (seller_id, id DESC);
ALTER TABLE sales ADD COLUMN commission_rule_id bigint REFERENCES commission_rules (id);

CREATE TABLE commission_accruals (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    seller_id bigint NOT NULL REFERENCES identity_users (id),
    sale_id bigint NOT NULL REFERENCES sales (id),
    settlement_id bigint UNIQUE REFERENCES finance_settlements (id),
    rule_id bigint NOT NULL REFERENCES commission_rules (id),
    base_minor bigint NOT NULL CHECK (base_minor > 0),
    amount_minor bigint NOT NULL CHECK (amount_minor >= 0),
    occurred_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX commission_sale_confirmation
    ON commission_accruals (sale_id) WHERE settlement_id IS NULL;

CREATE TABLE commission_reversals (
    accrual_id bigint PRIMARY KEY REFERENCES commission_accruals (id),
    actor_id bigint NOT NULL REFERENCES identity_users (id),
    reason varchar(240) NOT NULL,
    occurred_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE commission_payouts (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    seller_id bigint NOT NULL REFERENCES identity_users (id),
    actor_id bigint NOT NULL REFERENCES identity_users (id),
    amount_minor bigint NOT NULL CHECK (amount_minor > 0),
    method text NOT NULL,
    payment_currency varchar(3) NOT NULL CHECK (payment_currency IN ('USD', 'PYG')),
    title_id bigint NOT NULL UNIQUE REFERENCES finance_titles (id),
    settlement_id bigint NOT NULL UNIQUE REFERENCES finance_settlements (id),
    request_key uuid NOT NULL UNIQUE,
    occurred_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE commission_audit (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    seller_id bigint NOT NULL REFERENCES identity_users (id),
    actor_id bigint NOT NULL REFERENCES identity_users (id),
    action text NOT NULL,
    occurred_at timestamptz NOT NULL DEFAULT now()
);

ALTER VIEW administrative_audit RENAME TO administrative_audit_currency;
CREATE VIEW administrative_audit AS
SELECT * FROM administrative_audit_currency
UNION ALL
SELECT 'commissions', a.id, a.occurred_at, a.action, actor.username, 'seller', a.seller_id
FROM commission_audit a JOIN identity_users actor ON actor.id = a.actor_id;

COMMIT;
