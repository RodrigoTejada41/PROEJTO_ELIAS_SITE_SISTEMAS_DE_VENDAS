BEGIN;

ALTER TABLE identity_users ADD COLUMN totp_activation_hash bytea;
ALTER TABLE identity_users ADD COLUMN totp_activation_expires_at timestamptz;
ALTER TABLE identity_mfa_challenges ADD COLUMN setup_secret bytea;

COMMIT;
