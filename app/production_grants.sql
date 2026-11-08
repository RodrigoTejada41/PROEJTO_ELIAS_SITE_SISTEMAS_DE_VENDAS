GRANT SELECT ON
    identity_users, identity_sessions, identity_login_limits, administrative_audit,
    catalog_skus, catalog_images, inventory_movements, inventory_policy,
    inventory_entry_batches, commercial_parties, finance_settings, finance_titles,
    finance_settlements, finance_reversals, sales, sale_items, sale_receipts,
    fx_policy, fx_rates, commission_rules, commission_accruals, commission_reversals,
    commission_payouts, company_profile
TO esther_app;

GRANT INSERT ON
    identity_users, identity_sessions, identity_login_limits, identity_audit,
    catalog_skus, catalog_images, catalog_audit, inventory_movements, inventory_policy_audit,
    inventory_entry_batches, commercial_parties, commercial_party_audit,
    finance_settings, finance_titles, finance_settlements, finance_reversals, finance_audit,
    sales, sale_items, sale_receipts, sale_audit, fx_rates, fx_audit,
    commission_rules, commission_accruals, commission_reversals, commission_payouts,
    commission_audit, company_profile, company_audit
TO esther_app;

GRANT UPDATE ON
    identity_users, identity_login_limits, catalog_skus, catalog_images, inventory_policy,
    commercial_parties, finance_settings, finance_titles, sales, sale_items, fx_policy,
    company_profile
TO esther_app;
GRANT DELETE ON identity_sessions, catalog_images, sale_items TO esther_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON identity_mfa_challenges TO esther_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO esther_app;

GRANT SELECT ON fx_rates, fx_policy TO esther_fx;
GRANT INSERT (pyg_per_usd, source, published_at) ON fx_rates TO esther_fx;
GRANT UPDATE (checked_at) ON fx_rates TO esther_fx;
GRANT UPDATE (last_checked, next_check, last_error, reference_rate_id, active_rate_id)
    ON fx_policy TO esther_fx;
GRANT USAGE ON SEQUENCE fx_rates_id_seq TO esther_fx;
