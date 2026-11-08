BEGIN;

CREATE TABLE fx_rates (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pyg_per_usd numeric(18,6) NOT NULL CHECK (pyg_per_usd > 0 AND pyg_per_usd <= 1000000),
    source text NOT NULL CHECK (source IN ('manual', 'exchangerate_api')),
    published_at timestamptz NOT NULL,
    checked_at timestamptz NOT NULL DEFAULT now(),
    actor_id bigint REFERENCES identity_users (id),
    reason varchar(240),
    UNIQUE (source, published_at, pyg_per_usd)
);

CREATE TABLE fx_policy (
    id boolean PRIMARY KEY DEFAULT true CHECK (id),
    mode text NOT NULL DEFAULT 'manual' CHECK (mode IN ('manual', 'automatic')),
    active_rate_id bigint REFERENCES fx_rates (id),
    reference_rate_id bigint REFERENCES fx_rates (id),
    last_checked timestamptz,
    next_check timestamptz,
    last_error text
);

INSERT INTO fx_policy (id) VALUES (true);

CREATE TABLE fx_audit (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_id bigint NOT NULL REFERENCES identity_users (id),
    action text NOT NULL,
    occurred_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE catalog_skus ADD COLUMN usd_cost_minor bigint CHECK (usd_cost_minor BETWEEN 0 AND 999999999999);
ALTER TABLE catalog_skus ADD COLUMN usd_price_minor bigint CHECK (usd_price_minor BETWEEN 1 AND 999999999999);
ALTER TABLE sales ADD COLUMN fx_rate_id bigint REFERENCES fx_rates (id);
ALTER TABLE finance_titles ADD COLUMN fx_rate_id bigint REFERENCES fx_rates (id);

ALTER TABLE finance_settlements ADD COLUMN payment_currency varchar(3);
ALTER TABLE finance_settlements ADD COLUMN payment_amount_minor bigint;
ALTER TABLE finance_settlements ADD COLUMN fx_rate_id bigint REFERENCES fx_rates (id);

UPDATE finance_settlements s SET payment_currency = t.currency, payment_amount_minor = s.amount_minor
FROM finance_titles t WHERE t.id = s.title_id;

ALTER TABLE finance_settlements ALTER COLUMN payment_currency SET NOT NULL;
ALTER TABLE finance_settlements ALTER COLUMN payment_amount_minor SET NOT NULL;
ALTER TABLE finance_settlements ADD CHECK (payment_currency IN ('USD', 'PYG'));
ALTER TABLE finance_settlements ADD CHECK (payment_amount_minor BETWEEN 1 AND 999999999999);
ALTER TABLE finance_titles ADD CHECK ((currency = 'USD' AND scale = 2) OR (currency = 'PYG' AND scale = 0));
ALTER TABLE finance_settings ADD CHECK ((currency = 'USD' AND scale = 2) OR (currency = 'PYG' AND scale = 0));

INSERT INTO finance_settings (currency, scale) VALUES ('USD', 2) ON CONFLICT (id) DO NOTHING;

ALTER VIEW administrative_audit RENAME TO administrative_audit_core;
CREATE VIEW administrative_audit AS
SELECT * FROM administrative_audit_core
UNION ALL
SELECT 'fx', a.id, a.occurred_at, a.action, actor.username, 'fx', 1::bigint
FROM fx_audit a JOIN identity_users actor ON actor.id = a.actor_id;

COMMIT;
