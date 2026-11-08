BEGIN;

CREATE TABLE identity_users (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username varchar(64) NOT NULL UNIQUE,
    password_hash text NOT NULL,
    role text NOT NULL CHECK (role IN ('MASTER', 'OPERATOR')),
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX identity_single_master
    ON identity_users (role) WHERE role = 'MASTER';

CREATE TABLE identity_audit (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event text NOT NULL,
    user_id bigint NOT NULL REFERENCES identity_users (id),
    occurred_at timestamptz NOT NULL DEFAULT now()
);

COMMIT;
