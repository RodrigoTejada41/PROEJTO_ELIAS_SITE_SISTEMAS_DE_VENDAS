BEGIN;

CREATE VIEW administrative_audit AS
SELECT 'identity'::text AS source, a.id, a.occurred_at, a.event AS action,
       coalesce(actor.username, a.actor_db_role::text, target.username) AS actor,
       'user'::text AS entity, a.user_id AS target_id
FROM identity_audit a
JOIN identity_users target ON target.id = a.user_id
LEFT JOIN identity_users actor ON actor.id = a.actor_user_id
UNION ALL
SELECT 'catalog', a.id, a.occurred_at, a.action, actor.username, 'sku', a.sku_id
FROM catalog_audit a JOIN identity_users actor ON actor.id = a.actor_id
UNION ALL
SELECT 'inventory', m.id, m.occurred_at,
       CASE WHEN m.compensates_id IS NOT NULL THEN 'compensation'
            WHEN m.delta > 0 THEN 'entry' ELSE 'exit' END,
       actor.username, 'sku', m.sku_id
FROM inventory_movements m JOIN identity_users actor ON actor.id = m.actor_id
UNION ALL
SELECT 'contacts', a.id, a.occurred_at, a.action, actor.username, party.kind, a.party_id
FROM commercial_party_audit a
JOIN identity_users actor ON actor.id = a.actor_id
JOIN commercial_parties party ON party.id = a.party_id;

COMMIT;
