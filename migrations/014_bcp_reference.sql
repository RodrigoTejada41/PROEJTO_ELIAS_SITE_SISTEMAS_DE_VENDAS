BEGIN;

ALTER TABLE fx_rates DROP CONSTRAINT fx_rates_source_check;
ALTER TABLE fx_rates ADD CONSTRAINT fx_rates_source_check
    CHECK (source IN ('manual', 'exchangerate_api', 'bcp'));

ALTER TABLE fx_policy ALTER COLUMN mode SET DEFAULT 'automatic';
UPDATE fx_policy SET mode = 'automatic', active_rate_id = NULL,
    reference_rate_id = NULL, next_check = NULL, last_error = NULL WHERE id;

COMMIT;
