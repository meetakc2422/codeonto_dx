"""The only tables the assistant can read: views in the `assistant` schema. Each client-owned view filters on
assistant.scope_ok / outlet_ok / brand_ok, which accept a scope only when it carries a signature made with a secret the
assistant's database role cannot read, so a query cannot widen its own scope to another client or outlet."""

SQL = r"""
CREATE SCHEMA IF NOT EXISTS assistant;

CREATE TABLE IF NOT EXISTS assistant.scope_secret (secret text NOT NULL);

-- who the signed scope names: '*', '<client>' or '<client>/<outlet>,<outlet>'; NULL if the signature is wrong
CREATE OR REPLACE FUNCTION assistant.scope_who() RETURNS text
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE s text := current_setting('app.scope', true); who text; sig text; sec text;
BEGIN
  IF s IS NULL OR s = '' THEN RETURN NULL; END IF;
  who := split_part(s, ':', 1); sig := split_part(s, ':', 2);
  SELECT secret INTO sec FROM assistant.scope_secret LIMIT 1;
  IF sec IS NULL OR md5(sec || ':' || who) <> sig THEN RETURN NULL; END IF;
  RETURN who;
END $$;

CREATE OR REPLACE FUNCTION assistant.scope_ok(cid bigint) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE who text := assistant.scope_who();
BEGIN
  IF who IS NULL THEN RETURN false; END IF;
  RETURN who = '*' OR split_part(who, '/', 1) = cid::text;
END $$;

CREATE OR REPLACE FUNCTION assistant.outlet_ok(cid bigint, oid bigint) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE who text := assistant.scope_who();
BEGIN
  IF who IS NULL THEN RETURN false; END IF;
  IF who = '*' THEN RETURN true; END IF;
  IF split_part(who, '/', 1) <> cid::text THEN RETURN false; END IF;
  IF strpos(who, '/') = 0 THEN RETURN true; END IF;
  RETURN oid = ANY(string_to_array(split_part(who, '/', 2), ',')::bigint[]);
END $$;

CREATE OR REPLACE FUNCTION assistant.brand_ok(cid bigint, bid bigint) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE who text := assistant.scope_who();
BEGIN
  IF who IS NULL THEN RETURN false; END IF;
  IF who = '*' THEN RETURN true; END IF;
  IF split_part(who, '/', 1) <> cid::text THEN RETURN false; END IF;
  IF strpos(who, '/') = 0 THEN RETURN true; END IF;
  RETURN EXISTS (SELECT 1 FROM brand_outlets o WHERE o.brand_id = bid
                 AND o.id = ANY(string_to_array(split_part(who, '/', 2), ',')::bigint[]));
END $$;

CREATE OR REPLACE VIEW assistant.clients AS
  SELECT c.id AS client_id, c.name FROM clients c WHERE assistant.scope_ok(c.id);

CREATE OR REPLACE VIEW assistant.brands AS
  SELECT b.id AS brand_id, b.client_id, b.name AS brand, i.name AS industry, b.is_active
  FROM brands b JOIN industries i ON i.id = b.industry_id WHERE assistant.brand_ok(b.client_id, b.id);

CREATE OR REPLACE VIEW assistant.outlets AS
  SELECT o.id AS outlet_id, b.client_id, b.id AS brand_id, b.name AS brand, o.outlet_name, o.area, o.city, o.is_active,
         o.zomato_res_id, o.swiggy_id, o.google_location_id
  FROM brand_outlets o JOIN brands b ON b.id = o.brand_id WHERE assistant.outlet_ok(b.client_id, o.id);

CREATE OR REPLACE VIEW assistant.reviews AS
  SELECT r.id AS review_id, b.client_id, o.id AS outlet_id, b.name AS brand, o.outlet_name, o.area, r.platform,
         r.author_name, r.rating, r.body, r.sentiment, r.reviewed_at, r.reply_status
  FROM reviews r JOIN brand_outlets o ON o.id = r.outlet_id JOIN brands b ON b.id = o.brand_id
  WHERE assistant.outlet_ok(b.client_id, o.id);

CREATE OR REPLACE VIEW assistant.review_replies AS
  SELECT rp.id AS reply_id, rp.review_id, b.client_id, rp.body, rp.source, rp.status, rp.published_at
  FROM review_replies rp JOIN reviews r ON r.id = rp.review_id JOIN brand_outlets o ON o.id = r.outlet_id
  JOIN brands b ON b.id = o.brand_id WHERE assistant.outlet_ok(b.client_id, o.id);

CREATE OR REPLACE VIEW assistant.metrics_daily AS
  SELECT b.client_id, o.id AS outlet_id, b.name AS brand, o.outlet_name, o.area, m.platform, k.code AS kpi_code,
         k.name AS kpi_name, k.unit, k.aggregation, k.higher_is_better, md.code AS module, m.metric_date, m.value, m.weight
  FROM metric_daily m JOIN kpis k ON k.id = m.kpi_id JOIN modules md ON md.id = k.module_id
  JOIN brand_outlets o ON o.id = m.outlet_id JOIN brands b ON b.id = o.brand_id WHERE assistant.outlet_ok(b.client_id, o.id);

CREATE OR REPLACE VIEW assistant.stock_outs AS
  SELECT s.id AS stock_out_id, b.client_id, o.id AS outlet_id, b.name AS brand, o.outlet_name, o.area, s.platform,
         s.item_name, s.category, s.mealtime, s.is_active, s.log_date, s.first_detected_at, s.last_detected_at,
         s.restored_at, s.downtime_minutes, s.back_at
  FROM stock_outs s JOIN brand_outlets o ON o.id = s.outlet_id JOIN brands b ON b.id = o.brand_id
  WHERE assistant.outlet_ok(b.client_id, o.id);

CREATE OR REPLACE VIEW assistant.listing_profiles AS
  SELECT b.client_id, o.id AS outlet_id, b.name AS brand, o.outlet_name, o.area, p.platform, p.title, p.primary_category,
         p.website, p.photo_count, p.last_post_at, p.open_status, p.health_score, p.issues, p.fetched_at
  FROM listing_profiles p JOIN brand_outlets o ON o.id = p.outlet_id JOIN brands b ON b.id = o.brand_id
  WHERE assistant.outlet_ok(b.client_id, o.id);

CREATE OR REPLACE VIEW assistant.outlet_hours AS
  SELECT b.client_id, o.id AS outlet_id, b.name AS brand, o.outlet_name, h.platform, h.service_type, h.day,
         h.is_active, h.start_time, h.end_time
  FROM outlet_hours h JOIN brand_outlets o ON o.id = h.outlet_id JOIN brands b ON b.id = o.brand_id
  WHERE assistant.outlet_ok(b.client_id, o.id);

CREATE OR REPLACE VIEW assistant.alerts AS
  SELECT a.id AS alert_id, b.client_id, o.id AS outlet_id, b.name AS brand, o.outlet_name, a.kind, a.severity,
         a.title, a.detail, a.is_open, a.first_seen_at, a.resolved_at
  FROM alerts a JOIN brand_outlets o ON o.id = a.outlet_id JOIN brands b ON b.id = o.brand_id
  WHERE assistant.outlet_ok(b.client_id, o.id);

-- shared reference data (not client data)
CREATE OR REPLACE VIEW assistant.kpi_catalog AS
  SELECT k.code AS kpi_code, k.name AS kpi_name, md.code AS module, md.name AS module_name, k.unit, k.aggregation,
         k.higher_is_better, k.description
  FROM kpis k JOIN modules md ON md.id = k.module_id WHERE k.is_active;

CREATE OR REPLACE VIEW assistant.platform_catalog AS
  SELECT code AS platform, name, category FROM platforms WHERE is_active;
"""

# In its own constant: these views need the uptime tables, which come after the migration that runs SQL.
UPTIME_SQL = r"""
CREATE OR REPLACE VIEW assistant.offline_episodes AS
  SELECT e.id AS episode_id, b.client_id, o.id AS outlet_id, b.name AS brand, o.outlet_name, o.area, e.platform, e.is_active,
         e.log_date, e.first_detected_at, e.last_detected_at, e.restored_at, e.downtime_minutes
  FROM offline_episodes e JOIN brand_outlets o ON o.id = e.outlet_id JOIN brands b ON b.id = o.brand_id
  WHERE assistant.outlet_ok(b.client_id, o.id);

CREATE OR REPLACE VIEW assistant.uptime_daily AS
  SELECT b.client_id, o.id AS outlet_id, b.name AS brand, o.outlet_name, o.area, u.platform, u.day, u.checks, u.online_checks
  FROM outlet_uptime_daily u JOIN brand_outlets o ON o.id = u.outlet_id JOIN brands b ON b.id = o.brand_id
  WHERE assistant.outlet_ok(b.client_id, o.id);

DO $$ BEGIN
  IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'assistant_ro') THEN
    GRANT SELECT ON assistant.offline_episodes, assistant.uptime_daily TO assistant_ro;
  END IF;
END $$;
"""

# In its own constant for the same reason as UPTIME_SQL. Bank details and customer ids aren't stored at all.
PAYOUTS_SQL = r"""
CREATE OR REPLACE VIEW assistant.payout_cycles AS
  SELECT c.id AS cycle_id, b.client_id, o.id AS outlet_id, b.name AS brand, o.outlet_name, o.area, c.platform, c.start_date, c.end_date, c.payout_date,
         c.status, c.utr, c.net_payout, c.order_count, c.orders_total, c.adjustments, c.expected_payout, c.discrepancy,
         c.commissionable_total, c.service_fee_total, c.issues, c.reconciled_at
  FROM payout_cycles c JOIN brand_outlets o ON o.id = c.outlet_id JOIN brands b ON b.id = o.brand_id
  WHERE assistant.outlet_ok(b.client_id, o.id);

CREATE OR REPLACE VIEW assistant.payout_orders AS
  SELECT po.id AS payout_order_id, po.cycle_id, b.client_id, o.id AS outlet_id, b.name AS brand, o.area, c.utr, po.order_id, po.order_date, po.status,
         po.payment_mode, po.net_order_value, po.service_fee_pct, po.service_fee, po.fees_total, po.government_charges, po.other_deductions,
         po.net_deductions, po.net_additions, po.payout, po.settlement_status, po.settlement_date, po.unsettled_amount, po.issues
  FROM payout_orders po JOIN payout_cycles c ON c.id = po.cycle_id JOIN brand_outlets o ON o.id = c.outlet_id JOIN brands b ON b.id = o.brand_id
  WHERE assistant.outlet_ok(b.client_id, o.id);

DO $$ BEGIN
  IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'assistant_ro') THEN
    GRANT SELECT ON assistant.payout_cycles, assistant.payout_orders TO assistant_ro;
  END IF;
END $$;
"""
