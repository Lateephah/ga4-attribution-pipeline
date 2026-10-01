-- Staging model: channel spend, one row per (date, source, medium).
-- Thin pass-through: rename and select, no business logic.
-- `excluded` is carried through as `is_unattributable` so the dashboard can
-- tell "free channel" (spend = 0) apart from "unknown channel" (spend unknown).

select
    event_date,
    traffic_source,
    traffic_medium,
    session_count,
    spend_estimate,
    excluded as is_unattributable
from {{ source('staging_marketing', 'channel_spend_daily') }}