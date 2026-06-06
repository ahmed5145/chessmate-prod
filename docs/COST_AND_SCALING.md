# ChessMate Cost Analysis & Scalability Report

**Last updated:** 2026-06-06  
**AWS account:** `381492194867`, region **us-east-2**, environment **Chessmate-env-2**  
**Sources:** Live AWS CLI, reported billing (~**$43/mo**), repository code (`settings.py`, `docker-entrypoint.sh`, `tasks.py`, models)  
**User base:** ~21 auth users on prod (test accounts only; no real traffic yet)

---

## Part 1: Current AWS Cost Breakdown

### Measured infrastructure

| Resource | Configuration |
|----------|---------------|
| **EC2 (EB)** | 1× `t3.small`, Docker single container |
| **RDS** | `chessmate-db`, `db.t3.micro`, 20 GB `gp2`, single-AZ, private |
| **ALB** | 1× internet-facing, 3 AZs |
| **NAT Gateway** | **None** |
| **Public IPv4** | 2× ALB-managed (+ EC2 auto public IP) |
| **Redis** | Bundled in container (`127.0.0.1`) — not ElastiCache |
| **Celery** | 1 worker, `--concurrency=1`, `SEQUENTIAL_BATCH_ANALYSIS=true` (default) |
| **S3** | Buckets exist; core PGN/analysis stored in **PostgreSQL** |

### Bill vs estimates (us-east-2)

| Service | Reported | Est. full month | Fixed vs variable |
|---------|----------|-----------------|-------------------|
| Elastic Load Balancing | $10.17 | ~$16–22 | **Fixed** |
| RDS | $10.67 | ~$12 + ~$2 storage | **Fixed** |
| EC2 Compute | $10.53 | ~$15 | **Fixed** at 1 instance |
| VPC | $9.46 | ~$7–11 | Mostly **fixed** (public IPv4) |
| EC2-Other | $2.49 | ~$2–4 | EBS — **fixed** |
| **Total** | **~$43** | **~$43–55** | **~95% fixed** at current scale |

### VPC / IPv4

- **No NAT Gateway** (confirmed).
- Public IPv4 line item: `485 hrs × $0.005 ≈ $2.43` (subset of VPC total).
- RDS made private removes ~**$3.65/mo** per public RDS IP.

### Hidden / watch items

| Item | Risk |
|------|------|
| Stuck `in_progress` batches | CPU waste |
| OpenAI | ~$0.003–0.005 per 10-game batch — low |
| CloudWatch logs | Grows with traffic |
| Data transfer | Low at zero users |

### Right-sizing

| Resource | Verdict |
|----------|---------|
| `t3.small` | OK for first ~100 light users |
| `db.t3.micro` | OK for launch; 20 GB is far more than needed |
| ALB | Required for EB HTTPS |
| Web + Celery + Stockfish on one box | **Bottleneck under concurrent batches**, not oversize |

### Remove / downsize now

1. RDS private (done) — saves IPv4  
2. Do **not** add NAT Gateway (~$32+/mo)  
3. Do **not** enable Multi-AZ RDS yet  
4. Remove unused Grafana/Prometheus SG rules if not used  

---

## Part 2: Per-User Storage Cost

### Where data lives

| Data | Location |
|------|----------|
| Imported games | PostgreSQL `games.pgn` + metadata |
| Batch reports | `core_batchanalysisreport` JSONB fields |

### Estimates

| Component | Per game |
|-----------|----------|
| Import only | ~**6 KB** |
| Batch `per_game_results` | ~**30–80 KB** |

### RDS marginal cost formula

```
monthly_storage_cost ≈ (total_GB / 1024) × $0.115   # gp2 us-east-2
```

| Games (import only) | Data | Marginal $/mo |
|---------------------|------|---------------|
| 15 | ~90 KB | ~$0.00001 |
| 100 | ~600 KB | ~$0.00007 |
| 1000 | ~6 MB | ~$0.0007 |

**Storage is negligible** until very large libraries.

---

## Part 3: Analysis Pipeline Costs

### Pipeline (prod defaults)

- `BATCH_ANALYSIS_DEPTH = 14`
- `SEQUENTIAL_BATCH_ANALYSIS = true` — one game at a time
- `STOCKFISH_THREADS = 4`, `STOCKFISH_HASH_SIZE = 128` MB
- Subtask limits: soft **840s** / hard **900s** per game
- `BATCH_CREDITS_PER_GAME = 0` — batch free after import
- Import: **1 credit = 1 game**
- OpenAI: **gpt-4o-mini** × ~2 calls per batch (~$0.003)

### Formulas

```
T_game ≈ 4 minutes (midpoint; range 3–5)

C_ec2_per_minute = $15 / 43200 ≈ $0.000347/min   # t3.small allocated

C_stockfish(N) = N × T_game × C_ec2_per_minute
C_openai(N) ≈ $0.003 × ceil(N/10)
C_batch(N) = C_stockfish(N) + C_openai(N)
```

### Cost per batch size

| N games | Stockfish time | C_batch (approx.) |
|---------|----------------|-------------------|
| 1 | 4 min | ~$0.004 |
| 5 | 20 min | ~$0.01 |
| 15 | 60 min | ~$0.024 |
| 50 | 200 min | ~$0.074 |
| 100 | 400 min | ~$0.15 |

**Wall-clock and CPU contention** limit throughput before dollar cost.

---

## Part 4: Free Tier Sustainability

```
SIGNUP_BONUS_CREDITS = 15   # 15 imports
BATCH_CREDITS_PER_GAME = 0  # batch included
```

**Worst case per signup** (15-game batch): **~$0.02–0.03**

| Signups | Max variable (all full batch) |
|---------|-------------------------------|
| 100 | ~$2.50 |
| 500 | ~$12.50 |
| 1000 | ~$25 |

**Verdict:** Financially sustainable for hundreds of signups; **abuse** is a **capacity** risk, not a budget risk. Use rate limits.

---

## Part 5: Capacity

| Metric | Estimate (single t3.small) |
|--------|----------------------------|
| Concurrent light API users | 20–40 |
| Batches per day (10-game) | ~8–15 |
| Concurrent batches | **1** effectively |

### First bottlenecks

1. Stockfish CPU (shared with Gunicorn)  
2. Celery queue depth (1 worker)  
3. RDS connections (`db.t3.micro` ~80–100)  
4. Container memory under Stockfish load  

---

## Part 6: Monitoring (pre-launch)

| Metric | Tool |
|--------|------|
| EB CPU | CloudWatch alarm >80% |
| ALB 5xx / latency | CloudWatch |
| RDS connections / storage | CloudWatch |
| Celery / batch | EB logs: `analyze_batch_task`, `game=game_` |
| Visitors | Cloudflare Web Analytics |
| JS errors | Sentry |
| Stuck batches | Django Admin |

---

## Part 7: Scaling roadmap

### Stage 0 — Today

- **Cost:** ~$43–50/mo  
- **Infra:** 1× t3.small, db.t3.micro, ALB, bundled Redis  

### Stage 1 — ~100 users

- **Cost:** ~$50–70/mo  
- **Changes:** Rate limits, CPU monitoring  

### Stage 2 — ~1,000 users

- **Cost:** ~$120–200/mo  
- **Changes:** Dedicated worker (`t3.medium`), RDS `db.t3.small`, optional ElastiCache  

### Stage 3 — ~10,000 users

- **Cost:** ~$800–2,000+/mo  
- **Changes:** Multi-instance web, 3–5 batch workers, larger RDS, WAF  

---

## Part 8: Executive Summary

| Metric | Value |
|--------|-------|
| Monthly AWS burn | **~$43–55** |
| Per 10-game batch (variable) | **~$0.01–0.02** |
| Per signup (15 credits, full use) | **~$0.02–0.03** |

### Top 5 before launch

1. Deploy pending fixes; CloudWatch alarms  
2. Rate-limit signup / batch creation  
3. Run one clean 10-game batch end-to-end  
4. Ops via Django Admin (batches, credits)  
5. Cloudflare + Sentry monitoring  

### Top 5 do not do yet

1. NAT Gateway  
2. Multi-AZ RDS  
3. ElastiCache  
4. Full Grafana on EC2  
5. `eb ssh --setup` without maintenance window  

---

## UX note: batch duration expectations

Prod runs **sequential** Stockfish at depth **14**. Use **~3–5 minutes per game** plus **~2 minutes** for coaching when setting user-facing ETA (see `batchTimeEstimate.js` and `public/site-config/`).
