# GA4 E-Commerce Acquisition & Channel Attribution Pipeline

> **Live Dashboard:** [View Looker Studio Report](https://datastudio.google.com/reporting/92ef0c24-07e4-4ac1-8df2-53156db52ffc/page/wD89F)

An end-to-end ELT pipeline for GA4 first-touch attribution, session-based ad spend estimation, and Return on Ad Spend (ROAS) analysis built using **Python, BigQuery, dbt, and Looker Studio**.

---

## 📌 Business Overview & Core Findings

E-commerce acquisition reports often obscure paid marketing efficiency by blending paid and unpaid channels or relying on unverified assumptions. This project models first-touch acquisition, estimates channel-level spend using industry CPC benchmarks, and tests unit economics at scale.

### Key Insights:
* **Paid Search Operating at a Loss:** `google / cpc` generates **$0.58 in revenue per session** against an estimated benchmark cost of **$5.42/session**, resulting in an estimated **ROAS of 0.11** (an 89% loss on ad spend). Spend would need to drop below $0.58/session to break even.
* **Seasonal Demand Surges:** Revenue peaks sharply on **Nov 30 (Cyber Monday)** and **Dec 16 (Holiday Shipping Cutoff)** across organic, direct, and referral traffic.
* **Data Privacy Limitation:** Approximately **14% of total revenue** (`(data deleted)`) is redacted by GA4's privacy thresholding and remains unattributable to specific acquisition channels.

---

## 🏗️ Architecture & Data Pipeline

```text
[ GA4 Event Data ] ➔ [ Python ETL Scripts ] ➔ [ BigQuery Data Warehouse ] ➔ [ dbt Models & Tests ] ➔ [ Looker Studio Dashboard ]
