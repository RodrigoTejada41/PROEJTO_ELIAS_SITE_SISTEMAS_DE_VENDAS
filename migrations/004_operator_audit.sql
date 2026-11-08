BEGIN;

ALTER TABLE identity_audit
    ADD COLUMN actor_user_id bigint REFERENCES identity_users (id);

COMMIT;
