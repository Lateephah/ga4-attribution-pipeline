"""
load_channel_revenue.py

Loads daily GA4 purchase revenue by channel into BigQuery, as a sibling table
to channel_spend_daily. The two are joined later (in dbt) on
(event_date, traffic_source, traffic_medium) to compute ROAS.

Known limitation, stated plainly: `transactions` (COUNT DISTINCT transaction_id)
is unreliable in this dataset — several rows show real revenue with a
transaction count of 0, meaning transaction_id is sometimes null on purchase
events. Revenue is the trustworthy metric here; transaction count is not used
downstream because of this.
"""

import os

import pandas as pd

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "your-project-id")
DATASET_ID = "staging_marketing"
TABLE_ID = "channel_revenue_daily"


def extract_ga4_daily_revenue() -> list[dict]:
    """Queries BigQuery directly for daily purchase revenue by channel."""
    from google.cloud import bigquery
    client = bigquery.Client(project=PROJECT_ID)
    query = """
        SELECT
          CAST(PARSE_DATE('%Y%m%d', event_date) AS STRING) AS event_date,
          LOWER(COALESCE(traffic_source.source, '(direct)')) AS traffic_source,
          LOWER(COALESCE(traffic_source.medium, '(none)')) AS traffic_medium,
          SUM(ecommerce.purchase_revenue_in_usd) AS total_revenue,
          COUNT(DISTINCT ecommerce.transaction_id) AS transactions
        FROM
          `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
        WHERE
          event_name = 'purchase'
        GROUP BY 1, 2, 3
    """
    return client.query(query).to_dataframe().to_dict(orient="records")


def load_to_bigquery(df: pd.DataFrame, dry_run: bool = True):
    if dry_run:
        print(f"[dry run] Would load {len(df)} rows to {PROJECT_ID}.{DATASET_ID}.{TABLE_ID}")
        return

    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    destination = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        autodetect=True,
    )
    print(f"Uploading {len(df)} rows to {destination}...")
    job = client.load_table_from_dataframe(df, destination, job_config=job_config)
    job.result()
    print(f"Loaded {destination}.")


# Your real revenue query results (first 50 rows, spanning Nov 1-7)
REAL_REVENUE_SAMPLE = [
    {"event_date": "2020-11-01", "traffic_source": "(direct)", "traffic_medium": "(none)", "total_revenue": 332.0, "transactions": 0},
    {"event_date": "2020-11-01", "traffic_source": "shop.googlemerchandisestore.com", "traffic_medium": "referral", "total_revenue": 179.0, "transactions": 0},
    {"event_date": "2020-11-01", "traffic_source": "google", "traffic_medium": "organic", "total_revenue": 95.0, "transactions": 0},
    {"event_date": "2020-11-01", "traffic_source": "<other>", "traffic_medium": "referral", "total_revenue": 73.0, "transactions": 0},
    {"event_date": "2020-11-01", "traffic_source": "(data deleted)", "traffic_medium": "(data deleted)", "total_revenue": 60.0, "transactions": 0},
    {"event_date": "2020-11-01", "traffic_source": "<other>", "traffic_medium": "<other>", "total_revenue": 34.0, "transactions": 0},
    {"event_date": "2020-11-02", "traffic_source": "(data deleted)", "traffic_medium": "(data deleted)", "total_revenue": 2196.0, "transactions": 1},
    {"event_date": "2020-11-02", "traffic_source": "shop.googlemerchandisestore.com", "traffic_medium": "referral", "total_revenue": 719.0, "transactions": 1},
    {"event_date": "2020-11-02", "traffic_source": "google", "traffic_medium": "organic", "total_revenue": 640.0, "transactions": 1},
    {"event_date": "2020-11-02", "traffic_source": "(direct)", "traffic_medium": "(none)", "total_revenue": 632.0, "transactions": 1},
    {"event_date": "2020-11-02", "traffic_source": "<other>", "traffic_medium": "referral", "total_revenue": 313.0, "transactions": 1},
    {"event_date": "2020-11-02", "traffic_source": "<other>", "traffic_medium": "<other>", "total_revenue": 190.0, "transactions": 1},
    {"event_date": "2020-11-02", "traffic_source": "google", "traffic_medium": "cpc", "total_revenue": 79.0, "transactions": 0},
    {"event_date": "2020-11-02", "traffic_source": "<other>", "traffic_medium": "organic", "total_revenue": 20.0, "transactions": 1},
    {"event_date": "2020-11-03", "traffic_source": "(direct)", "traffic_medium": "(none)", "total_revenue": 868.0, "transactions": 1},
    {"event_date": "2020-11-03", "traffic_source": "(data deleted)", "traffic_medium": "(data deleted)", "total_revenue": 823.0, "transactions": 1},
    {"event_date": "2020-11-03", "traffic_source": "shop.googlemerchandisestore.com", "traffic_medium": "referral", "total_revenue": 463.0, "transactions": 1},
    {"event_date": "2020-11-03", "traffic_source": "google", "traffic_medium": "organic", "total_revenue": 407.0, "transactions": 1},
    {"event_date": "2020-11-03", "traffic_source": "<other>", "traffic_medium": "<other>", "total_revenue": 294.0, "transactions": 1},
    {"event_date": "2020-11-03", "traffic_source": "<other>", "traffic_medium": "referral", "total_revenue": 225.0, "transactions": 1},
    {"event_date": "2020-11-03", "traffic_source": "<other>", "traffic_medium": "organic", "total_revenue": 183.0, "transactions": 1},
    {"event_date": "2020-11-03", "traffic_source": "google", "traffic_medium": "cpc", "total_revenue": 50.0, "transactions": 1},
    {"event_date": "2020-11-04", "traffic_source": "google", "traffic_medium": "organic", "total_revenue": 569.0, "transactions": 1},
    {"event_date": "2020-11-04", "traffic_source": "(data deleted)", "traffic_medium": "(data deleted)", "total_revenue": 481.0, "transactions": 1},
    {"event_date": "2020-11-04", "traffic_source": "(direct)", "traffic_medium": "(none)", "total_revenue": 321.0, "transactions": 1},
    {"event_date": "2020-11-04", "traffic_source": "<other>", "traffic_medium": "referral", "total_revenue": 303.0, "transactions": 1},
    {"event_date": "2020-11-04", "traffic_source": "<other>", "traffic_medium": "<other>", "total_revenue": 252.0, "transactions": 1},
    {"event_date": "2020-11-04", "traffic_source": "<other>", "traffic_medium": "organic", "total_revenue": 123.0, "transactions": 1},
    {"event_date": "2020-11-04", "traffic_source": "google", "traffic_medium": "cpc", "total_revenue": 87.0, "transactions": 1},
    {"event_date": "2020-11-04", "traffic_source": "shop.googlemerchandisestore.com", "traffic_medium": "referral", "total_revenue": 61.0, "transactions": 1},
    {"event_date": "2020-11-05", "traffic_source": "(data deleted)", "traffic_medium": "(data deleted)", "total_revenue": 441.0, "transactions": 1},
    {"event_date": "2020-11-05", "traffic_source": "(direct)", "traffic_medium": "(none)", "total_revenue": 380.0, "transactions": 1},
    {"event_date": "2020-11-05", "traffic_source": "<other>", "traffic_medium": "<other>", "total_revenue": 319.0, "transactions": 1},
    {"event_date": "2020-11-05", "traffic_source": "shop.googlemerchandisestore.com", "traffic_medium": "referral", "total_revenue": 269.0, "transactions": 1},
    {"event_date": "2020-11-05", "traffic_source": "<other>", "traffic_medium": "referral", "total_revenue": 215.0, "transactions": 1},
    {"event_date": "2020-11-05", "traffic_source": "google", "traffic_medium": "cpc", "total_revenue": 87.0, "transactions": 1},
    {"event_date": "2020-11-05", "traffic_source": "<other>", "traffic_medium": "(data deleted)", "total_revenue": 63.0, "transactions": 1},
    {"event_date": "2020-11-05", "traffic_source": "google", "traffic_medium": "organic", "total_revenue": 18.0, "transactions": 1},
    {"event_date": "2020-11-06", "traffic_source": "google", "traffic_medium": "organic", "total_revenue": 1455.0, "transactions": 1},
    {"event_date": "2020-11-06", "traffic_source": "(direct)", "traffic_medium": "(none)", "total_revenue": 938.0, "transactions": 1},
    {"event_date": "2020-11-06", "traffic_source": "<other>", "traffic_medium": "referral", "total_revenue": 402.0, "transactions": 1},
    {"event_date": "2020-11-06", "traffic_source": "shop.googlemerchandisestore.com", "traffic_medium": "referral", "total_revenue": 350.0, "transactions": 1},
    {"event_date": "2020-11-06", "traffic_source": "<other>", "traffic_medium": "<other>", "total_revenue": 153.0, "transactions": 1},
    {"event_date": "2020-11-06", "traffic_source": "(data deleted)", "traffic_medium": "(data deleted)", "total_revenue": 116.0, "transactions": 1},
    {"event_date": "2020-11-06", "traffic_source": "google", "traffic_medium": "cpc", "total_revenue": 24.0, "transactions": 1},
    {"event_date": "2020-11-07", "traffic_source": "google", "traffic_medium": "organic", "total_revenue": 1342.0, "transactions": 1},
    {"event_date": "2020-11-07", "traffic_source": "(direct)", "traffic_medium": "(none)", "total_revenue": 347.0, "transactions": 1},
    {"event_date": "2020-11-07", "traffic_source": "shop.googlemerchandisestore.com", "traffic_medium": "referral", "total_revenue": 283.0, "transactions": 1},
    {"event_date": "2020-11-07", "traffic_source": "<other>", "traffic_medium": "<other>", "total_revenue": 233.0, "transactions": 1},
    {"event_date": "2020-11-07", "traffic_source": "google", "traffic_medium": "cpc", "total_revenue": 139.0, "transactions": 1},
]


if __name__ == "__main__":
    DRY_RUN = False

    if DRY_RUN:
        print("Running dry run with sample data...\n")
        records = REAL_REVENUE_SAMPLE
    else:
        print("Extracting live GA4 revenue from BigQuery...\n")
        records = extract_ga4_daily_revenue()

    df = pd.DataFrame(records)
    df["event_date"] = pd.to_datetime(df["event_date"]).dt.date

    print(df.to_string(index=False))
    print(f"\nTotal rows: {len(df)}")
    print(f"Rows with revenue but 0 recorded transactions: {len(df[(df['total_revenue'] > 0) & (df['transactions'] == 0)])}")

    load_to_bigquery(df, dry_run=DRY_RUN)
    