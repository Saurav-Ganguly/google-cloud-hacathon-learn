# Cloud Run Pricing

**Source**: https://cloud.google.com/run/pricing
**Model**: Pay per use, billed in 100ms increments. Scale to zero — no charge when idle.

---

## Free Tier (per month, resets monthly, aggregated across all projects under one billing account)

| Resource type | CPU free | RAM free |
|---|---|---|
| Services (instance-based) | 240,000 vCPU-seconds | 450,000 GiB-seconds |
| Services (request-based) | 180,000 vCPU-seconds | 360,000 GiB-seconds |
| **Jobs (cron workloads)** | **240,000 vCPU-seconds** | **450,000 GiB-seconds** |
| Worker pools | 384,204 vCPU-seconds | 728,744 GiB-seconds |
| Requests (request-based only) | 2 million requests | — |

---

## Rates After Free Tier (us-central1 Tier 1, no CUD)

| Resource | Rate |
|---|---|
| CPU (Jobs / instance-based) | $0.000018 / vCPU-second |
| RAM (Jobs / instance-based) | $0.000002 / GiB-second |
| CPU (request-based, active) | $0.000024 / vCPU-second |
| RAM (request-based, active) | $0.0000025 / GiB-second |
| Requests | $0.40 / million |

Minimum billing for Jobs: **1 minute** per execution (even if it finishes in 10 seconds).

---

## Cron Job Cost Estimate

Scenario: a few cron jobs per day, ~2 total active hours/day, 1 vCPU + 512 MiB config.

| Period | CPU-seconds | RAM GiB-seconds | Cost |
|---|---|---|---|
| Per day | 7,200 | 3,600 | — |
| Per month (30 days) | 216,000 | 108,000 | — |
| Free tier | 240,000 | 450,000 | — |
| **Overage** | **0** | **0** | **$0.00** |

**For this workload: $0/month.** Both CPU and RAM stay within the free tier.

If you double to 4 hrs/day:
- CPU overage: 432,000 - 240,000 = 192,000 × $0.000018 = **~$3.46/month**
- RAM still within free tier

The real cost for an AI agent will be **Gemini API calls**, not Cloud Run compute.

---

## Key Things to Know

- **Jobs** = best billing model for cron workloads. Billed for full execution time, min 1 minute.
- **Services** = for HTTP endpoints, scales to zero between requests.
- **Scale to zero** = no charge when nothing is running. Cron jobs are perfect for this.
- **Region matters**: Tier 1 (us-central1, europe-west1, etc.) is cheapest. Tier 2 (Singapore, London, etc.) costs more.
- India (Mumbai = asia-south1) is Tier 1 — same price as Iowa.

---

## Related

- [[concepts/agent-runtime]] — Managed PaaS alternative to raw Cloud Run
- [[resources/agent-platform-onboard/notes]] — deployment walkthrough via agents-cli
- [[hackathon/resources]] — Phase 5 deployment resources
