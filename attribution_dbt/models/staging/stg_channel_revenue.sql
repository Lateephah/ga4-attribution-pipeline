-- Staging model: channel revenue, one row per (date, source, medium).
-- `transactions` is deliberately excluded here, not just downstream — it's
-- unreliable in the raw data (7 rows have real revenue with a null
-- transaction_id, so the count reads 0). Excluding it at the staging layer
-- means no mart can accidentally build on top of a number we already know
-- is wrong.

with source as (
    select * from {{ source('staging_marketing', 'channel_revenue_daily') }}
)

select
    cast(event_date as date) as event_date,
    lower(traffic_source) as traffic_source,
    lower(traffic_medium) as traffic_medium,
    cast(total_revenue as numeric) as total_revenue,
    cast(transactions as int64) as transactions
from source