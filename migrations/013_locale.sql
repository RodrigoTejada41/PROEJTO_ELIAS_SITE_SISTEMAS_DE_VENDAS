BEGIN;

ALTER TABLE identity_users ADD COLUMN preferred_locale text NOT NULL DEFAULT 'pt'
    CHECK (preferred_locale IN ('pt', 'es'));

COMMIT;
