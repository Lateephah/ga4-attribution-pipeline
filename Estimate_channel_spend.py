"""
estimate_channel_spend.py (v3, session-based)

Estimates daily ad spend per channel from GA4 session counts, then loads the
result into BigQuery for dbt to join against daily revenue.

What changed from v2, and why:
v2 multiplied EVENT counts by CPC. CPC is cost per click, and one click starts
one session, which fires ~13 events in this dataset (google/cpc: 1,381 events
over 108 sessions on 2020-11-01). Counting events overstated spend ~13x. v3
counts `session_start` events instead: one session ~ one click.

Methodology, stated plainly:
- Only `google / cpc` is a genuinely paid channel here. Every other clean
  source/medium combination is unpaid by definition: spend is $0.
- `google / cpc` spend = session_count * MEDIAN_GOOGLE_SEARCH_CPC. This is an
  ESTIMATE from a published cross-industry benchmark, not real spend (real
  spend isn't public and isn't in this dataset).
- `(data deleted)` and `<other>` rows are flagged and excluded, not zeroed:
  "unknown" and "free" are different claims.

Known limitations (state these in the dashboard too):
- GA4's `traffic_source` field is user-scoped first-acquisition attribution:
  the source that first acquired the user, not the session that converted.
- The sample dataset is obfuscated by Google; it doesn't reconcile like a
  real store's data.
- Whether ROAS lands above or below 1 depends almost entirely on the CPC
  assumption. Revenue per session (computed in dbt) does not.

Credentials: set GOOGLE_APPLICATION_CREDENTIALS and GCP_PROJECT_ID as
environment variables. Never hardcode a key path in a file bound for GitHub.
"""

import os
from dataclasses import dataclass, field

import pandas as pd

# USD. Source: WordStream/LocaliQ 2026 Google Ads Benchmarks (13,000+ campaigns,
# 23 industries, published as a median). This is the ALL-INDUSTRY blended
# figure; the same report breaks out per-industry medians, and a retail /
# e-commerce figure would fit this dataset better than the blended average.
MEDIAN_GOOGLE_SEARCH_CPC = 5.42

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "your-project-id")
DATASET_ID = "staging_marketing"
TABLE_ID = "channel_spend_daily"


@dataclass
class ChannelRow:
    event_date: str
    traffic_source: str
    traffic_medium: str
    session_count: int
    spend_estimate: float = field(default=0.0)
    excluded: bool = field(default=False)
    exclusion_reason: str = field(default="")


def is_paid_search(source: str, medium: str) -> bool:
    return source.strip().lower() == "google" and medium.strip().lower() == "cpc"


def is_redacted_or_unknown(source: str, medium: str) -> tuple[bool, str]:
    combined = f"{source} {medium}".lower()
    if "data deleted" in combined:
        return True, "GA4 privacy-threshold redaction: not recoverable, not $0"
    if "<other>" in combined:
        return True, "GA4 long-tail bucketing: source/medium not individually broken out"
    return False, ""


def estimate_spend(rows: list[dict]) -> list[ChannelRow]:
    results = []
    for r in rows:
        row = ChannelRow(
            event_date=str(r["event_date"]),
            traffic_source=r["traffic_source"],
            traffic_medium=r["traffic_medium"],
            session_count=int(r["session_count"]),
        )
        excluded, reason = is_redacted_or_unknown(row.traffic_source, row.traffic_medium)
        if excluded:
            row.excluded = True
            row.exclusion_reason = reason
        elif is_paid_search(row.traffic_source, row.traffic_medium):
            row.spend_estimate = round(row.session_count * MEDIAN_GOOGLE_SEARCH_CPC, 2)
        else:
            row.spend_estimate = 0.0
        results.append(row)
    return results


def to_dataframe(rows: list[ChannelRow]) -> pd.DataFrame:
    df = pd.DataFrame([r.__dict__ for r in rows])
    df["event_date"] = pd.to_datetime(df["event_date"]).dt.date
    return df


def extract_ga4_daily_sessions() -> list[dict]:
    """Queries BigQuery directly for daily session counts by source/medium."""
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    query = """
        SELECT
          CAST(PARSE_DATE('%Y%m%d', event_date) AS STRING) AS event_date,
          LOWER(COALESCE(traffic_source.source, '(direct)')) AS traffic_source,
          LOWER(COALESCE(traffic_source.medium, '(none)')) AS traffic_medium,
          COUNTIF(event_name = 'session_start') AS session_count
        FROM
          `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
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
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,  # idempotent on rerun
        autodetect=True,
    )
    print(f"Uploading {len(df)} rows to {destination}...")
    job = client.load_table_from_dataframe(df, destination, job_config=job_config)
    job.result()
    print(f"Loaded {destination}.")


def print_daily_summary(df: pd.DataFrame):
    summary = (
        df[~df["excluded"]]
        .groupby("event_date")["spend_estimate"]
        .sum()
        .reset_index()
        .rename(columns={"spend_estimate": "total_estimated_spend"})
    )
    print(summary.to_string(index=False))


# Real query output (first 32 rows, Nov 1-4 2020), used as an offline test fixture
_SAMPLE = [
    ("2020-11-01", "google", "organic", 824), ("2020-11-01", "(direct)", "(none)", 611),
    ("2020-11-01", "<other>", "<other>", 370), ("2020-11-01", "<other>", "referral", 255),
    ("2020-11-01", "shop.googlemerchandisestore.com", "referral", 212),
    ("2020-11-01", "(data deleted)", "(data deleted)", 123), ("2020-11-01", "google", "cpc", 108),
    ("2020-11-01", "<other>", "organic", 88), ("2020-11-01", "<other>", "(data deleted)", 3),
    ("2020-11-02", "google", "organic", 1099), ("2020-11-02", "(direct)", "(none)", 821),
    ("2020-11-02", "<other>", "<other>", 529), ("2020-11-02", "<other>", "referral", 360),
    ("2020-11-02", "shop.googlemerchandisestore.com", "referral", 321),
    ("2020-11-02", "(data deleted)", "(data deleted)", 261), ("2020-11-02", "google", "cpc", 175),
    ("2020-11-02", "<other>", "organic", 109), ("2020-11-02", "<other>", "(data deleted)", 7),
    ("2020-11-03", "google", "organic", 1682), ("2020-11-03", "(direct)", "(none)", 1234),
    ("2020-11-03", "<other>", "<other>", 742), ("2020-11-03", "<other>", "referral", 511),
    ("2020-11-03", "shop.googlemerchandisestore.com", "referral", 402),
    ("2020-11-03", "(data deleted)", "(data deleted)", 329), ("2020-11-03", "google", "cpc", 238),
    ("2020-11-03", "<other>", "organic", 137), ("2020-11-03", "<other>", "(data deleted)", 10),
    ("2020-11-04", "google", "organic", 1310), ("2020-11-04", "(direct)", "(none)", 954),
    ("2020-11-04", "<other>", "<other>", 630), ("2020-11-04", "<other>", "referral", 410),
    ("2020-11-04", "shop.googlemerchandisestore.com", "referral", 373),
]
REAL_SAMPLE_DATA = [
    {"event_date": d, "traffic_source": s, "traffic_medium": m, "session_count": n}
    for d, s, m, n in _SAMPLE
]


if __name__ == "__main__":
    # Set DRY_RUN = False once credentials are configured and you're ready to
    # query BigQuery for real and write the result table.
    DRY_RUN = True

    if DRY_RUN:
        print("Running dry run with sample data...\n")
        rows = estimate_spend(REAL_SAMPLE_DATA)
    else:
        print("Extracting live GA4 sessions from BigQuery...\n")
        rows = estimate_spend(extract_ga4_daily_sessions())

    df = to_dataframe(rows)
    print("Paid-search rows:\n")
    print(df[df["spend_estimate"] > 0].to_string(index=False))
    print(f"\nRows: {len(df)} | excluded as unattributable: {int(df['excluded'].sum())}")
    print("\nDaily totals (excluded rows removed from the sum):\n")
    print_daily_summary(df)
    load_to_bigquery(df, dry_run=DRY_RUN)