# 02 — Streaming Token Delivery

**Prompt:** Design streaming token delivery for a large-scale chat product (and matching API) with reconnect, fairness, and global users.

**Rank:** Top 10 (#02)

## Use cases

| Use case | Who | Why this design matters |
|----------|-----|-------------------------|
| Live chat UI | Web/mobile assistants | Perceived latency = TTFT + smooth token drip |
| IDE / coding copilots | Editors with inline stream | Cancel, partial accept, reconnect after laptop sleep |
| Voice / realtime assistants | Speech-to-speech products | Tight inter-token budgets; often WebSocket not SSE |
| API streaming for apps | Developers building on your models | Resume, backpressure, fair multi-tenant stream slots |
| Collaborative playground | Shared session demos | Multiple viewers, one generation, sequenced events |

---

## 1. Clarify requirements

### Functional
- Stream tokens to web, mobile, and API clients as they are generated.
- Support cancel, regenerate, and mid-stream stop.
- Reconnect after network blips without duplicating or losing content (best effort).
- Multipart outputs: text, tool calls, citations, safety interruptions.

### Non-functional
| Metric | Target |
|--------|--------|
| TTFT P99 | ≤ 500 ms (consumer), tighter for API |
| Inter-token gap P99 | ≤ 50 ms once decoding |
| Reconnect resume | Within last 1–2 seconds of tokens |
| Fanout | Millions concurrent streams |
| Ordering | Strict per conversation turn |

### Scale axes
- Concurrent streams
- Tokens/s egress bandwidth
- Geographic distance (RTT)
- Message size (tool payloads, images later)

### Unacceptable failures
- Reordered tokens within a turn
- Duplicate assistant messages after refresh
- Stuck spinner with no timeout
- One tenant starving stream slots

---

## 2. Protocol choice

| Option | Pros | Cons | Use |
|--------|------|------|-----|
| **SSE** | Simple, HTTP/2 friendly, CDN-friendly | One-way; proxies buffer if misconfigured | Default for chat + many APIs |
| **WebSocket** | Bidirectional, cancel easy | Sticky connections, harder at edge | Voice, collaborative, tool-heavy agents |
| **gRPC streaming** | Strong typing, multiplex | Client ecosystem | Internal / enterprise SDK |

**Recommendation:** SSE for Chat/API text streaming; WebSocket for realtime multimodal / voice.

Critical: disable proxy buffering (`X-Accel-Buffering: no`), flush per event, use HTTP/2 or HTTP/3.

---

## 3. High-level architecture

```
Client ← Edge SSE/WS termination ← Stream Gateway ← Generation Orchestrator
                                              ↑
                                    Inference Worker (token events)
                                              ↓
                                    Stream State Store (Redis / memory)
```

### Components
1. **Stream Gateway** — terminates client connections; auth; backpressure.
2. **Generation Orchestrator** — owns turn lifecycle: prompt → model → safety → persist.
3. **Token bus** — internal pub/sub from worker to gateway (or pull).
4. **Stream State Store** — `generation_id`, last `seq`, buffered recent tokens, status.
5. **Conversation Store** — durable final message after completion (or incremental checkpoints).

---

## 4. Event model

```text
event: meta
data: {"generation_id":"g_123","model":"x","created":...}

event: token
data: {"seq":1,"text":"Hello"}

event: token
data: {"seq":2,"text":" world"}

event: tool_call
data: {"seq":3,"name":"search","args":{...}}

event: safety
data: {"action":"block","category":"..."}

event: done
data: {"finish_reason":"stop","usage":{...}}
```

- Monotonic **`seq`** per generation enables resume.
- Clients ACK optionally; server retains a **ring buffer** of last N events (e.g. 5–10s).

---

## 5. Deep dive: backpressure & fairness

### Backpressure
- If client is slow (mobile network), **do not** block the GPU forever.
- Policy options:
  1. Buffer up to B KB then disconnect with resume token.
  2. Coalesce tokens into larger SSE events (hurts perceived latency).
  3. For API: apply client read deadlines; cancel generation on breach for free tier.

Principal line: **GPU time is more expensive than dropping a slow free-tier stream.**

### Fairness
- Limit concurrent streams per user/org.
- Separate connection pools: interactive vs API batch-with-stream.
- At gateway: max streams per host; shed with 503 + `Retry-After`.

### Cost–latency coupling (say this)
> “Longer generations cost more tokens and hold KV + stream state longer. Streaming doesn’t remove that—it surfaces it. Meter both tokens and stream-minutes for abuse control.”

---

## 6. Reconnect & idempotency

1. Client stores `generation_id` + last `seq`.
2. On reconnect: `GET /stream?generation_id=g_123&after_seq=40`.
3. Gateway replays from ring buffer; if expired, return `410` + point client to durable store for completed text.
4. **Idempotent finalize:** only one writer commits the assistant message using conditional write on `turn_id`.

### Race: double tab / double submit
- Client sends `idempotency_key` for the user turn.
- Orchestrator dedupes; second request attaches to same `generation_id`.

---

## 7. Global distribution

```
User → nearest edge PoP → regional Stream Gateway → regional Inference
```

- Prefer **inference in-region** to keep TTFT low; don’t hairpin tokens across oceans.
- Sticky session: `generation_id` hashed to region; reconnect must route same region (or replicate state).
- State store: Redis with short TTL (minutes) is enough for resume; durable DB for final transcript.

| Scale | Breakage | Fix |
|-------|----------|-----|
| 10× streams | Gateway FD / CPU | Horizontal gateway; connectionless design where possible |
| 100× | Redis hot keys | Shard by `generation_id`; local memory + async replicate |
| 1000× | Cross-region failover | Active-active regions; sticky generation affinity |

---

## 8. Safety during streaming

- Run output classifiers on **rolling windows**, not only final text.
- On high-risk span: emit `safety` event, stop tokens, optionally rewrite/refusal.
- Never stream raw tool args that contain secrets to untrusted clients.
- Audit: store redacted stream or hash + policy decision for compliance.

---

## 9. Observability

- Metrics: TTFT, inter-token latency, disconnect rate, resume success %, buffer evictions, cancel rate.
- Trace: `request_id` → `generation_id` → worker_id.
- Alert: P99 inter-token spike (often GPU overload) vs disconnect spike (edge/network).

---

## 10. Multi-year bet

**Bet:** Make **`generation_id` + seq log** the universal streaming abstraction across chat, API, voice, and agents—so reconnect, audit, and tool events share one pipeline. Keep SSE as the external default; invest in a regional low-latency event fabric internally.

---

## 11. 60-second summary

Terminate streams at the edge, own turn state in an orchestrator, emit sequenced events, and resume via short-lived buffers. Apply backpressure that protects GPUs, keep inference regional for TTFT, and interrupt streams safely when classifiers fire.
