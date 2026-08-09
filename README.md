# Use Case: Realtime Creative Tools

**Design doc:** [docs/DESIGN.md](./docs/DESIGN.md) — architecture, patterns, and why.


**Parent system design:** [10 — Global Realtime Product Surface](../10-global-realtime-product-surface.md)

## Users & problem

Writing/image/video assistants generate creatively with live progress. Spiky viral load and heavy media make 10×/100×/1000× planning mandatory.

## Requirements & SLOs

| Requirement | Target |
|-------------|--------|
| Progress | Stream partial text or render previews |
| Media | Async jobs for heavy renders |
| Scale | Cells + separate media workers |
| Cost | Clear quotas on generations |

## Design (from parent)

```
Creative UI → conversation/project store
  → text via LLM stream ([02](../02-streaming-token-delivery.md))
  → media via job queue + object store
  → webhook/UI progress events
```

Apply **10** cell/scale pressure tests; don’t put multi-minute renders on interactive GPU chat pools ([01](../01-llm-inference-serving.md)).

## Specializations

| Concern | Creative choice |
|---------|-----------------|
| Projects | Assets + versions, not only chat turns |
| Collaboration | Shared projects ([02 collaborative](../collaborative-playground/README.md)) |
| Moderation | Output safety on media+text ([06](../06-safety-moderation-pipeline.md)) |
| CDN | Asset delivery at edge |

## Failure modes

- Viral template → per-template rate limits + cell isolation.
- Interactive fleet used for video → hard separate pools.
- Lost assets → durable object store + job state machine.



## Run (self-contained POC)

This folder is a **standalone** project (safe to split into its own GitHub repo).

```bash
cd realtime-creative-tools
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
PYTHONPATH=. python -m uvicorn app.main:app --reload --port 8000
```

```bash
curl -s http://127.0.0.1:8000/health | jq
```

curl -s -X POST http://127.0.0.1:8000/projects/p1/generate -H 'Content-Type: application/json' -d '{"kind":"text","prompt":"tagline"}' | jq
