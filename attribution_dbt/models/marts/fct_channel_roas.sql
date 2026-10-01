-- Mart: daily channel performance. The table the dashboard reads from.
--
-- Deliberate decisions, encoded here rather than left implicit:
-- 1. LEFT JOIN spend -> revenue. A channel that spent money and sold nothing
--    that day is a real row; an inner join would silently delete it.
-- 2. 2021-01-27 through 2021-01-31 are excluded (the dataset's final 5 days).
--    2021-01-31 shows $0 revenue across every channel simultaneously: a
--    collection cutoff, not a finding. The four days before it (01-27 to
--    01-30) showed google/cpc at exactly $0 revenue for 4 straight days —
--    checked against the channel's own 91-day base rate (29.7% of all days
--    are $0 for this channel, so a 4-day zero streak occurs by chance alone
--    roughly once per 91-day window) and found statistically unremarkable,
--    but positioned suspiciously close to a confirmed data boundary. Treated
--    as likely pipeline degradation near the export cutoff, not a real trend,
--    and excluded on that basis rather than presented as a finding.
-- 3. Two metrics, on purpose:
--      roas                 depends on the ASSUMED cost per click, so treat it
--                           as an estimate, not a fact.
--      revenue_per_session  needs no cost assumption. For a paid channel it is
--                           also the break-even CPC: the most you could pay per
--                           click and still not lose money.
-- 4. Attribution is first-touch (GA4's traffic_source is the source that first
--    acquired the user), not the session that converted.

with spend as (
    select * from {{ ref('stg_channel_spend') }}
),

revenue as (
    select * from {{ ref('stg_channel_revenue') }}
),

joined as (
    select
        spend.event_date,
        spend.traffic_source,
        spend.traffic_medium,
        spend.session_count,
        spend.spend_estimate,
        spend.is_unattributable,
        coalesce(revenue.total_revenue, 0) as total_revenue
    from spend
    left join revenue
        on spend.event_date = revenue.event_date
        and spend.traffic_source = revenue.traffic_source
        and spend.traffic_medium = revenue.traffic_medium
)

select
    event_date,
    traffic_source,
    traffic_medium,
    session_count,
    spend_estimate,
    is_unattributable,
    total_revenue,
    case
        when spend_estimate > 0 then round(total_revenue / spend_estimate, 3)
        else null
    end as roas,
    case
        when session_count > 0 then round(total_revenue / session_count, 3)
        else null
    end as revenue_per_session
from joined
where event_date not between '2021-01-27' and '2021-01-31'  -- data collection boundary, see note 2
order by event_date desc, spend_estimate desc