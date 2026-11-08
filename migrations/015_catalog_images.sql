BEGIN;

CREATE TABLE catalog_images (
    sku_id bigint PRIMARY KEY REFERENCES catalog_skus (id),
    image bytea NOT NULL CHECK (octet_length(image) BETWEEN 1 AND 2097152)
);

COMMIT;
