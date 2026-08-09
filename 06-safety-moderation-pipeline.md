# 06 — Multi-Layer Safety / Moderation Pipeline

**Prompt:** Design a multi-layered content safety system for an LLM product that balances harm prevention, latency, and over-refusal—under regulatory and reputational constraints.

**Rank:** Top 10 (#06)

## Use cases

| Use case | Who | Why this design matters |
|----------|-----|-------------------------|
| Consumer chat content policy | Mass-market AI apps | Layered filters + streaming interrupt |
| Developer API moderation | Third-party apps | Consistent decisions, reason codes, audit |
| Enterprise custom policies | Regulated / brand-safe orgs | Policy packs without forking the stack |
| Education / restricted modes | Schools, family products | Stricter fail-closed categories |
| Red-team / jailbreak defense | Trust & safety | Ensembles, tool-bypass prevention |

---

## 1. Clarify requirements

### Functional
- Block or refuse disallowed categories (e.g. child exploitation, violent crimes assistance, scams, weapons, etc.—use company policy taxonomy).
- Allow benign edge cases; minimize over-refusal.
- Support streaming: interrupt mid-generation.
- Auditability for trust & safety / compliance.
- Enterprise policy packs (custom allow/deny).

### Non-functional
| Metric | Example target |
|--------|----------------|
| Added latency P95 | ≤ 30–50 ms for cheap layers; total safety budget ≤ ~50–100 ms excluding main model |
| High-severity miss rate | Extremely low (policy-defined); page on spike |
| Over-refusal | Tracked & budgeted like an SLO |
| Availability | Prefer fail-closed for highest severity; nuanced elsewhere |

### Unacceptable failures
- High-severity content reaching users at scale
- Safety service outage silently disabling filters
- Inconsistent decisions across chat vs API
- Unauditable blocks (no reason codes)

---

## 2. Layered architecture (defense in depth)

```
User input
  → L0: rules / regex / hash blocklists (≤5 ms)
  → L1: lightweight prompt classifier (≤15 ms)
  → Policy router (which model, which tools allowed)
  → Main LLM (constitution / system policy aligned)
  → L2: streaming output classifier on rolling windows
  → L3: async secondary review + human queues for borderline
  → Audit log
```

**Framing:** safety is an architectural constraint—parallel classifiers, policy-aligned model behavior, async compliance—not a single “moderation API” bolted on.

---

## 3. Deep dive: latency budget & fail modes

### Budget example (interactive chat ~200–500 ms TTFT overall)
| Stage | Budget |
|-------|--------|
| L0 + L1 input | 15–20 ms |
| Auth / quota | 10 ms |
| Queue / prefill start | remainder |
| Output classifier per window | ≤10–15 ms overlapping decode |

Overlap output classification with decoding so you rarely add full serial latency.

### Fail-open vs fail-closed
| Category severity | Safety service down | Behavior |
|-------------------|---------------------|----------|
| Critical | Fail-closed | Refuse / degrade to safe model only |
| Medium | Fail-open with stricter template | Log loudly; page |
| Low | Fail-open | Metric + ticket |

**Never** fail-open on critical categories to “preserve availability.”

---

## 4. Decision types

- **Allow**
- **Refuse** (model or policy message)
- **Safe-complete** (answer high-level, no actionable harm)
- **Block + terminate stream**
- **Escalate** (async human review; may disable features for account)

Emit machine-readable `reason_code` + policy version for every decision.

---

## 5. Training vs runtime policy

| Mechanism | Role |
|-----------|------|
| Pretraining / RLHF / constitutional training | Broad behavioral prior |
| System prompts / policy specs | Product-tunable behavior |
| Runtime classifiers | Hard enforcement + measurable gates |
| Tool permissioning | Prevent bypass via browsing/code |

Principal line: *Don’t rely on the model alone for hard safety guarantees; don’t rely on classifiers alone for nuanced refusal quality.*

---

## 6. Adversarial robustness

- Jailbreak paraphrases, many-shot, encoded payloads, multimodal stegos.
- Retrieve-then-attack via RAG (poisoned docs).
- Tool-based bypass (model refuses but browser executes).

Mitigations: input normalization, classifier ensembles, output filters on tool results, sandbox permissions independent of model text.

---

## 7. Evaluation & governance

- Offline red-team suites per category; track miss / false positive rates.
- Canary: safety metrics are **ship gates** equal to latency.
- Policy changes versioned; A/B carefully—safety isn’t a pure growth metric.
- Clear ownership: Trust & Safety + Eng on-call for pipeline; Research for model behavior.

---

## 8. Scale 10× / 100× / 1000×

| Scale | Breakage | Fix |
|-------|----------|-----|
| 10× QPS | Classifier GPU pool | Distilled models; CPU for L0/L1; batch classify |
| 100× languages | English-centric miss | Multilingual classifiers; per-locale eval |
| 1000× enterprise policies | Rule explosion | Policy-as-data engine; compile to efficient matchers |

---

## 9. Multi-year bet

**Bet:** Standardize a **Safety Decision Plane**—versioned policies, layered detectors, unified reason codes—consumed by chat, API, and agents. Keep critical enforcement **out of band** from the main model so capability gains don’t silently weaken hard limits.

**Why:** Capability and safety must scale together; organizationally, a shared plane beats per-product forks.

---

## 10. 60-second summary

Stack cheap deterministic filters, fast classifiers, aligned model behavior, and streaming output checks with explicit fail-closed rules for critical harm. Budget latency via overlap, version every policy decision, and gate deploys on safety slices—not just average block rate.
