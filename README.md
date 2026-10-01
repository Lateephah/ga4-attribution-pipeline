# GA4 Attribution & ROAS Pipeline

A cloud-native data pipeline that estimates paid-search spend, joins it against real GA4 e-commerce revenue, and surfaces an honest return-on-ad-spend view in a live dashboard — built on BigQuery, dbt, and Looker Studio.

**Live dashboard:** [View Looker Studio Report](https://datastudio.google.com/reporting/92ef0c24-07e4-4ac1-8df2-53156db52ffc/page/wD89F)

**Stack:** Python (ingestion) → BigQuery (warehouse) → dbt (transformation + testing) → Looker Studio (presentation)

## What this does, and for whom

Marketing and analytics teams need to know whether a channel is actually worth paying for, not just how much traffic it brings. This pipeline takes Google's own public GA4 e-commerce sample dataset, estimates what paid search would have cost using a published industry benchmark, and joins that against real purchase revenue to answer the one question that matters: is this channel profitable?

The honest answer this pipeline surfaces: **estimated paid search ROAS is 0.11** — roughly 11 cents back for every dollar of estimated spend. That's the kind of plainly-stated, uncomfortable number a real attribution project should be able to produce and defend, not smooth over.

## Setup (reproducible from scratch)

**Prerequisites:** a Google Cloud project with BigQuery enabled, Python 3.10+, dbt-bigquery.

1. **Create a service account** in GCP (IAM & Admin → Service Accounts), with `BigQuery Data Editor` and `BigQuery Job User` roles. Download its JSON key.
2. **Set environment variables** (never commit the key file itself):
   ```
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"
   export GCP_PROJECT_ID="your-project-id"
   ```
3. **Create a BigQuery dataset** named `staging_marketing` in your project.
4. **Install dependencies:**
   ```
   pip install pandas google-cloud-bigquery dbt-bigquery
   ```
5. **Run the two ingestion scripts** (in `scripts/`), each with `DRY_RUN = False` set:
   ```
   python scripts/estimate_channel_spend.py
   python scripts/load_channel_revenue.py
   ```
   This populates `channel_spend_daily` and `channel_revenue_daily` in BigQuery.
6. **Run dbt** (from the `dbt/` directory):
   ```
   dbt deps
   dbt run
   dbt test
   ```
   This builds `fct_channel_roas` — the table the dashboard reads from — and runs 7 data tests against it.
7. **Connect Looker Studio** to `fct_channel_roas` via BigQuery as the data source.

## Usage example

Querying the final table for any channel's performance:
```sql
SELECT event_date, traffic_source, traffic_medium, spend_estimate, total_revenue, roas, revenue_per_session
FROM `your-project.staging_marketing.fct_channel_roas`
WHERE traffic_source = 'google' AND traffic_medium = 'cpc'
ORDER BY event_date DESC
```

## Architecture

```
GA4 public dataset (BigQuery)
      │
      ├── estimate_channel_spend.py ──► channel_spend_daily
      │   (sessions × published CPC benchmark)
      │
      └── load_channel_revenue.py ───► channel_revenue_daily
          (real purchase revenue by channel)
                      │
                      ▼
            dbt: stg_channel_spend, stg_channel_revenue
                      │
                      ▼
            dbt: fct_channel_roas (LEFT JOIN, ROAS + revenue_per_session)
                      │
                      ▼
              Looker Studio dashboard
```

## Key findings (v1)

- **Paid search is estimated to operate at a loss**: ROAS of 0.11, revenue per session of $0.58 against an assumed $5.42 CPC. This holds even allowing for uncertainty in the CPC assumption — spend would need to fall below $0.58/session to break even.
- **~14% of total revenue is unattributable** (`(data deleted)`), redacted by GA4's own privacy thresholding — not a pipeline defect, but a real ceiling on how complete this attribution can ever be.
- Revenue peaks coincide with Cyber Monday (Nov 30, 2020) and a mid-December shipping-cutoff date — consistent with known retail seasonality, though causation wasn't independently verified beyond the date alignment.

## Limitations

- **Spend is estimated, not real.** Calculated as paid-search session count × a published cross-industry median CPC ($5.42, WordStream/LocaliQ 2026 benchmark). Real spend data isn't available in this public dataset.
- **Attribution is first-touch.** GA4's `traffic_source` field records the channel that first acquired the user, not the session that converted. A channel's "revenue" here means revenue from users it originally brought in, whenever they eventually bought.
- **The dataset's final 5 days (Jan 27–31, 2021) are excluded.** Jan 31 shows $0 revenue across every channel simultaneously — a confirmed data collection cutoff. The four days before it showed a suspicious pattern too close to that same boundary to trust as a genuine trend, and were excluded on the same basis after checking the channel's broader 91-day base rate.
- **The dataset is obfuscated by Google**, and its own documentation states transaction counts and revenue won't fully reconcile the way a real store's data would — the `transactions` field specifically was found unreliable (real revenue recorded against a null transaction ID on several rows) and is excluded from all downstream logic.

## Built with AI — what, and how

This pipeline's logic, dbt models, and this README were developed in collaboration with Claude (Anthropic). Several real errors were caught and corrected during development, not hidden after the fact: an initial spend-estimation approach multiplied CPC by raw event counts instead of sessions, overstating spend roughly 13x, caught by checking the resulting ROAS against plausibility rather than accepting it; a first CPC benchmark figure was cited without being independently verified and was corrected once checked against a properly sourced report; a GA4 field bug (`traffic_source.name` instead of `.source`) was caught and fixed after producing nonsensical results. Every number in the Key Findings section above was checked against the underlying data before being stated as a finding, including ruling out two separate data-boundary artifacts that could otherwise have been mistaken for real trends.
