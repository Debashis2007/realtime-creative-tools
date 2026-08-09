# Design: Realtime Creative Tools

**Project:** `realtime-creative-tools`  
**Parent system design:** `10-global-realtime-product-surface.md`

## 1. What this POC demonstrates

Text stays on interactive pool; heavy media goes to separate worker pool/job.

## 2. Architecture (POC)

```text
POST /projects/{id}/generate kind=text|media → pool selection
```

## 3. Patterns used (and why)

| Pattern | Why used | Where in code |
|---------|----------|---------------|
| Workload pool split | Video/image must not block chat GPUs. | `media-workers` vs `interactive`. |
| Job id for media | Long renders need async UX. | `job_*` + asset URI. |
| Project namespacing | Creative tools are asset-centric. | `projects/{pid}`. |

## 4. Key endpoints

`GET /health`, `POST /projects/{pid}/generate`

## 5. Tradeoffs / POC limits

Media job completes instantly with fake S3 URI.

## 6. How to run

See the **Run (self-contained POC)** section in [`../README.md`](../README.md).

This folder is self-contained and can be published as its own GitHub repository.

## 7. Design walkthrough video

> **Watch on YouTube:** [Realtime Creative Tools — System Design #Shorts](https://youtu.be/-7la9Ws6XjQ)
>
> Direct link: **https://youtu.be/-7la9Ws6XjQ**

Also available in-repo:
- GIF preview: [`video/design-overview.gif`](./video/design-overview.gif)
- MP4 download: [`video/design-overview.mp4`](./video/design-overview.mp4)
- Narration script: [`video/narration.txt`](./video/narration.txt)

