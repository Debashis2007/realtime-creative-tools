# 01 — LLM Inference Serving at Scale

**Prompt:** Design a low-latency inference platform that serves a frontier LLM to millions of concurrent users (consumer chat + developer API scale).

**Rank:** Top 10 (#01)

## Use cases

| Use case | Who | Why this design matters |
|----------|-----|-------------------------|
| Consumer AI chat | Millions of concurrent users | Continuous batching + KV management keep TTFT/cost viable |
| Developer completions / chat API | Third-party apps, high TPM | Multi-tenant isolation, quotas, predictable P99 |
| Enterprise private model hosting | Single-tenant or VPC-style | Dedicated pools, stronger SLO and data isolation |
| Multi-model SaaS product | App with small + frontier models | Shared control plane, separate fleets by model size |
| Long-context document analysis | 100K–1M token prompts | KV/HBM becomes the scarce resource; needs dedicated tier |

---

## 1. Clarify requirements (lead this)

### Functional
- Serve chat + API completions for one or more model sizes (e.g. 8B / 70B / frontier).
- Streaming and non-streaming responses.
- Multi-tenant: consumer, Plus, enterprise, API with different SLOs.
- Model versioning, canaries, and instant rollback.

### Non-functional (propose concrete SLOs)
| Metric | Consumer chat | API (paid) |
|--------|---------------|------------|
| Time-to-first-token (TTFT) P99 | ≤ 500 ms | ≤ 300 ms |
| Inter-token latency P99 | ≤ 50 ms | ≤ 30 ms |
| Availability | 99.9% | 99.95% |
| Max context | 128K–1M tokens (tiered) | Same |
| Fairness | Soft quotas | Hard rate limits |

### Scale axes (name them explicitly)
1. **Request rate** (QPS)
2. **Prompt / generation length** (tokens)
3. **Model size** (params → GPU memory)
4. **Concurrency** (KV cache residency)
5. **Tenancy** (noisy neighbors)

### Unacceptable failures
- Silent wrong-model routing
- Cross-tenant data leakage via cache
- Cascade OOM from long-context storms
- Stuck generations with no timeout

---

## 2. Capacity sketch (example numbers)

Assume: **100K concurrent sessions**, avg **30 tokens/s** generation, avg prompt 2K tokens, completion 500 tokens.

- Aggregate output: `100K × 30 ≈ 3M tokens/s`
- If one H100-class GPU sustains ~**2–5K tokens/s** for a mid-size model with continuous batching (order-of-magnitude; depends on model/quantization), you need **hundreds to thousands of GPUs** for a frontier model at this concurrency.
- Memory: KV cache often dominates. Rough: `2 × layers × heads × dim × seq × bytes × batch`. At long context, **KV cache, not weights**, is the bottleneck.

Principal signal: *“We scale with concurrent context bytes in GPU HBM, not just QPS.”*

---

## 3. High-level architecture

```
Client → Edge (TLS, WAF) → API Gateway (auth, quota, request ID)
       → Safety ingress (cheap filters)
       → Router (model, region, priority tier)
       → Inference Scheduler / Queue
       → GPU Worker Pool (continuous batching engines)
       → Safety egress (output classifiers, async audit)
       → Stream back to client
```

### Key components
1. **API Gateway** — auth, API keys, org quotas, idempotency keys.
2. **Router** — picks model revision, region, and priority queue.
3. **Scheduler** — packs requests into continuous batches; admits/rejects based on KV headroom.
4. **Workers** — vLLM / TensorRT-LLM / custom engine; tensor/pipeline parallel as needed.
5. **KV Cache Manager** — prefix cache, session stickiness, eviction policy.
6. **Control plane** — model registry, canary %, autoscaler, drain for deploys.
7. **Observability** — TTFT, tokens/s/GPU, batch size, KV hit rate, queue wait.

---

## 4. Deep dive: continuous batching + KV cache

### Continuous batching
- Don’t wait for a full static batch. As sequences finish, admit new prompts into free slots.
- Cap: `max_batch_tokens` and `max_batch_seqs` to bound latency.
- Admission control: if queue wait > SLO budget, shed low-priority or return 429.

### KV cache strategy
| Technique | Win | Cost |
|-----------|-----|------|
| PagedAttention-style paging | Fragmentation ↓, util ↑ | Complexity |
| Prefix / prompt cache | Shared system prompts, RAG prefixes | Cross-tenant isolation risk |
| Speculative decoding | TTFT / throughput ↑ for draft+verify | Extra small model capacity |
| Quantization (FP8/INT4 weights) | More models per GPU | Quality regression risk |

### Parallelism choice
- **Tensor parallel**: latency-sensitive single request across GPUs in a node.
- **Pipeline parallel**: larger models; watch bubble time.
- **Replica (data) parallel**: scale QPS with independent copies.
- Principal framing: start with **replicas of TP shards**; only deepen PP when a single replica doesn’t fit.

### Quantified tradeoff example (say this out loud)
> “A 200MB per-session KV budget at 128K context means we can host ~N concurrent sessions per GPU. Raising max context 4× without paging drops concurrency ~4× or forces CPU offload that blows P99. I’d rather tier long-context to a dedicated pool than poison the interactive fleet.”

---

## 5. Multi-tenancy & fairness

- **Priority queues**: interactive chat > batch API > offline eval.
- **Token buckets** per org + global GPU token budget.
- **Isolation**: separate pools for enterprise / long-context / research canaries.
- **Noisy neighbor**: cap max concurrent seqs per tenant on a worker.

---

## 6. Reliability & scale (10× / 100× / 1000×)

| Scale | What breaks | Mitigation |
|-------|-------------|------------|
| 10× | Queue wait, TTFT | Autoscale replicas; tighten admission |
| 100× | HBM / networking / control plane | Regional shards; hierarchical schedulers; prefix cache at edge of region |
| 1000× | Power, supply chain, single-region risk | Multi-region active-active; model distillation for cheap tier; capacity reservations |

### Failure modes
- **GPU OOM** → preemption of lowest priority + circuit breaker on long prompts.
- **Worker death mid-stream** → client reconnect with `generation_id`; resume if state checkpointed, else graceful error.
- **Bad model deploy** → canary on 1% traffic with automatic rollback on TTFT/error/safety spike.

---

## 7. Safety (first-class, not bolt-on)

- Cheap input filters before GPU spend.
- Output streaming with overlapping classifiers; hold/abort on high-risk spans.
- Audit log: request_id, model_version, safety decisions, latency breakdown.
- Fail-closed for enterprise policy modes; fail-open with soft filters only where product explicitly allows.

---

## 8. Multi-year architectural bet

**Bet:** Treat **KV cache as a first-class cluster resource** (scheduled, accounted, charged) equal to FLOPs. Build a regional prefix-cache fabric and separate interactive vs long-context fleets early. Prefer continuous batching + strong admission control over naive horizontal scale of naive engines.

**Why:** At frontier context lengths, memory residency—not raw TFLOPs—dominates cost and SLO violations.

---

## 9. Common follow-ups & crisp answers

| Probe | Answer direction |
|-------|------------------|
| How do you pick batch size? | Maximize tokens/s subject to TTFT/ITL SLO; measure, don’t guess |
| Prefix cache cross-tenant? | Hash with tenant salt; never share across trust domains |
| Why not always biggest batch? | Tail latency; prefill vs decode interference |
| Cost vs latency? | Route short/cheap prompts to smaller models; reserve frontier for hard queries |

---

## 10. 60-second summary

Build a routed, admission-controlled continuous-batching fleet where **GPU HBM for KV** is the primary scarce resource. Separate pools by SLO and context length, canary every model revision, and instrument TTFT / tokens-per-GPU / KV hit rate as the operational north stars.
