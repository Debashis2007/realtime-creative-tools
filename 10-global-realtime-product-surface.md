# 10 — Global Realtime Product Surface

**Prompt:** Design a global realtime product (consumer chat, playground, or streaming media companion) and pressure-test it at 10× / 100× / 1000×.

**Rank:** Top 10 (#10)

## Use cases

| Use case | Who | Why this design matters |
|----------|-----|-------------------------|
| Global consumer AI chat | Web + mobile worldwide | Cells, home region, durable messages, streaming |
| Model playground | Developers trying models | Full-stack: auth, sync, attachments, entitlements |
| Multi-device assistant | Phone + laptop continuity | Conversation sync with seq / idempotency |
| Realtime creative tools | Writing, image, video assistants | 10×/100×/1000× pressure on hot shards + GPUs |
| Team / workspace AI product | Shared threads in orgs | ACL on conversations; regional residency |

---

## 1. Clarify requirements

This round often starts broad on purpose. **You** must narrow it.

### Example product framing (state it)
“Consumer + Pro chat app: auth, conversation sync, streaming answers, light file upload, multi-device, global users.”

### Functional
- Accounts, conversations, streaming messages, edits/regenerates.
- Attachments → ingest → optional RAG within thread.
- Settings: model choice, memory (if any), privacy modes.
- Admin: abuse, bans, status page hooks.

### Non-functional
| Metric | Target |
|--------|--------|
| TTFT P99 | ≤ 500 ms regional |
| Message sync | Multi-device eventual < 1–2 s |
| Availability | 99.9% with regional degradation |
| Durability | No lost sent user messages |

### Scale axes (explicit)
Users → concurrent sessions → tokens/s → storage of histories → fanout of sync.

### Unacceptable failures
- Lost user prompts
- Cross-user conversation leak
- Global hard down from one region
- Unbounded cost from abuse loops

---

## 2. Lead with numbers

Assume **100M MAU**, **10M DAU**, peak **1M concurrent**, avg session generates **1K tokens**.

- Peak tokens/s order: hundreds of thousands to millions depending on concurrency assumptions—reconcile with inference capacity (tie to doc 01).
- History storage: `messages × bytes`; plan cold tiering for old threads.
- Sync QPS: every token event can’t fan out naively to all devices—coalesce.

---

## 3. High-level architecture

```
Clients (web/mobile)
  → Edge CDN / PoP
  → App BFF / API (auth, conversations)
  → Stream layer (SSE) → Inference platform
  → Conversation service + store
  → Attachment / RAG services
  → Safety plane
  → Push / sync notifier
  → Analytics / monitoring
```

### Service split
| Service | Responsibility |
|---------|----------------|
| Identity | AuthN/Z, sessions |
| Conversation | CRUD threads, ACLs |
| Generation | Orchestrate model calls |
| Media | Uploads, virus scan, store |
| Sync | Device fanout of new messages |
| Safety | Ingress/egress policy |
| Billing/Entitlements | Plan limits |

---

## 4. Deep dive: conversation consistency

### Write path
1. Persist user message **first** (durable) with `client_message_id` idempotency.
2. Enqueue generation job.
3. Stream tokens to devices; periodically checkpoint partial assistant message (optional).
4. Finalize assistant message; mark turn complete.

### Read / sync
- Devices poll or subscribe to `thread_id` event log (seq numbers).
- Authoritative store: primary DB (e.g. regionally partitioned); caches are hints.
- Conflict: edits/regenerate create new message versions; don’t rewrite history silently.

**Principal line:** *User message durability beats fancy streaming. Never lose the prompt even if GPUs melt.*

---

## 5. Global multi-region

| Approach | Pros | Cons |
|----------|------|------|
| Active-passive | Simpler consistency | Failover pain |
| Active-active sticky users | Lower latency | Cross-region complexity |
| Regional home + redirect | Good balance | Migration on travel |

Recommendation: **user home region** for conversation primary; edge for static; inference in-region when capacity allows. On regional outage: read-only histories + queued sends, or promote secondary with conflict rules.

---

## 6. Full-stack expectations

Worth covering end-to-end:
- **Client:** optimistic UI, reconnect with `generation_id`, offline send queue.
- **API contract:** message seq, error codes, rate limits.
- **Schema:** threads, messages, attachments, generations.
- **Abuse:** content spam, bot farms, credential stuffing.
- **Cost:** cache, smaller models for cheap tiers, attachment size caps.

Don’t stop at backend boxes.

---

## 7. Scale pressure test (the heart of this round)

| Scale | What breaks first | Mitigation |
|-------|-------------------|------------|
| **10×** | DB hotspot on hot threads; gateway connections | Shard by `user_id`/`thread_id`; more stream gateways |
| **100×** | Inference capacity; Redis/sync fanout | Separate interactive GPU pools; coalesce sync events; regional cells |
| **1000×** | Org/process limits: deploy risk, config, single bus | Cell architecture (independent stacks per N users); strict blast radius |

Speak to **cells**: each cell owns a user shard end-to-end (app + DB + stream). Global directory maps user → cell. Outage of one cell ≠ global outage.

---

## 8. Safety, privacy, abuse

- Same layered safety as doc 06 on every generation.
- Encryption in transit; at-rest encryption; enterprise ZDR modes.
- Rate limits per user/device/IP; anomaly detection on token burn.
- Memory features: explicit user control; hard delete paths.

---

## 9. Observability

- Product: send success, TTFT, regenerate rate, crash loops.
- Funnel: auth → first message → retention.
- Cell health dashboards; per-cell error budgets.

---

## 10. Multi-year bet

**Bet:** **Cell-based product + regional inference** with a thin global control plane (identity, billing, model registry). Optimize for blast-radius containment and home-region latency over a single globally consistent chat DB.

**Why:** At global consumer scale, regional and cell failures are inevitable; architecture must degrade, not brick the brand.

---

## 11. How to structure a 60-minute walkthrough

1. Minutes 0–5: scope product + SLOs + axes  
2. 5–15: high-level + data model  
3. 15–35: deep dive (sync, streaming, or inference interface)  
4. 35–50: 10×/100×/1000× + failures  
5. 50–60: safety, privacy, multi-year bet  

---

## 12. 60-second summary

Pin a clear product scope, durable-first conversation writes, regional streaming to inference, and a cell architecture that survives 1000× by isolation. Full-stack: client reconnect, API contracts, entitlements, and safety—then pressure-test hot shards, GPU capacity, and fanout at each order of magnitude.
