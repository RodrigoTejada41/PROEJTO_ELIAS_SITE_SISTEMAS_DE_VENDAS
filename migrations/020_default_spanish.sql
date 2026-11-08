BEGIN;

ALTER TABLE identity_users ALTER COLUMN preferred_locale SET DEFAULT 'es';

COMMIT;
