BEGIN;

ALTER TABLE identity_audit ADD COLUMN actor_db_role name;

COMMIT;
