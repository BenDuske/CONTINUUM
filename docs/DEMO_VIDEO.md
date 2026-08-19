# CONTINUUM — 90-Second Demo Video Script & Shot List

*Deliverable for Agentic Cinema Hackathon (Sep 7, 2026 deadline). Target
length: 90s (hard cap: 3:00 per rules). Upload to YouTube unlisted or
Vimeo, then embed in `README.md` above-the-fold.*

## The story we're telling in 90 seconds

> A director wants to wrap Scene 42. CONTINUUM's agents refuse — and show
> exactly why, in the language a script supervisor speaks. That refusal
> is the product.

## Recording setup (do once)

- **Screen recording:** OBS Studio (free) or QuickTime.
- **Capture area:** 1920×1080, browser only. Hide bookmarks bar.
- **Audio:** ElevenLabs (Brian) narration exported as WAV, mixed under video
  in DaVinci Resolve (free). No music.
- **URL to hit:** the live Cloud Run URL,
  `https://continuum-882642985987.us-central1.run.app` — real ClickHouse Cloud,
  real Gemini pipeline. (Local dev fine as a backup.)
- **Pre-load:** open the dashboard once so agents warm up (first agent call
  is slow — the MCP toolset lazy-inits).

## Shot list (90s target — 6 shots × ~15s)

| # | Duration | Visual | Narration (write it out — read cold) |
|---|----------|--------|--------------------------------------|
| 1 | 0:00–0:12 | Title card: `CONTINUUM — Know you have the movie before you leave the set.` Fade to dashboard homepage. | "Every day on set, a hundred small decisions decide whether a film gets finished. CONTINUUM is an agentic system that watches all of them at once." |
| 2 | 0:12–0:25 | Scroll dashboard: 6 agents (Director, StoryGraph, Continuity, FinalTake, Cascade, Skeptic). Highlight the "Wrap Check" button on Scene 42. | "Six specialist agents, one production graph in ClickHouse Cloud, one Gemini brain. Let's ask the hard question." |
| 3 | 0:25–0:45 | Click Scene 42 → click WRAP CHECK. Show the request firing. Cut to Cloud Run logs (or a terminal tailing them) showing the agent pipeline: Director routes → FinalTake queries `shots` and `takes` → Continuity queries `props` → Skeptic verifies. | "The Director routes to Final Take, who counts shots against captured takes. Continuity notices Camera P-14 is damaged — that must show in every take. Skeptic checks for a script revision that would override the finding. There isn't one." |
| 4 | 0:45–1:05 | Verdict lands on screen: 🔴 **NOT SAFE TO WRAP.** Missing shots 42G and 42H. Camera P-14 damage continuity flagged. Coverage 75%. | "Verdict: do not wrap. Two shots missing, and every reshoot has to preserve the damaged camera. The system tells you what to shoot before the crew leaves the location." |
| 5 | 1:05–1:20 | Cut to `compliance/` folder view + LICENSE header. Then flash: "Gemini + ADK · ClickHouse MCP · Google Cloud Run · Apache 2.0". | "Built on Gemini 3.5 Flash and Google's Agent Development Kit. Production memory in ClickHouse Cloud, accessed at runtime through the official `mcp-clickhouse` server. Open source, Apache 2.0." |
| 6 | 1:20–1:30 | Closing card: `CONTINUUM · continuum-882642985987.us-central1.run.app · github.com/BenDuske/CONTINUUM` | "CONTINUUM. Because 'we'll fix it in post' was always a lie." |

## Beats you must land (judging criteria mapping)

| Beat | Judging criterion it satisfies |
|------|-------------------------------|
| The refusal (shot 4) | **Idea Quality** — this is the pitch in one frame |
| Multi-agent pipeline visible (shot 3) | **Technical Implementation** |
| Real Cloud Run + real ClickHouse (shot 2–3) | **Technical Implementation** |
| Dashboard UI (shots 1, 2, 4) | **Design** |
| "Before the crew leaves the location" (shot 4) | **Potential Impact** — this is real money saved |

## Do NOT

- Do not show Claude, ChatGPT, or Anthropic anywhere on screen (hackathon DQ risk).
- Do not show credentials, `.env`, GCP account emails, or ClickHouse
  connection strings.
- Do not exceed 3:00. 90s is the target for judge attention.

## Recording checklist

- [ ] Browser zoom = 100%. Clear cache so no autofill leaks.
- [ ] Cloud Run service warmed (hit `/` first, then wait 5s).
- [ ] `gcloud run services logs tail continuum --region us-central1` open in a
      side terminal (for shot 3 pipeline visibility).
- [ ] Narration recorded and normalized to –16 LUFS.
- [ ] Export: 1920×1080, H.264, 8 Mbps, MP4.
- [ ] Upload target: YouTube (unlisted) — Devpost accepts YouTube/Vimeo.
- [ ] Update `README.md` — replace the placeholder demo-video section with
      the real embed once the link exists.
- [ ] Update the Devpost submission's "video" field with the same link.

## README embed snippet (paste when link ready)

```markdown
## 🎬 Demo (90s)

[![CONTINUUM demo](https://img.youtube.com/vi/<VIDEO_ID>/maxresdefault.jpg)](https://youtu.be/<VIDEO_ID>)

Watch the signature scenario: *"Can we wrap Scene 42?" → 🔴 NOT SAFE TO WRAP*
in 90 seconds.
```

*Argo — 2026-08-19*
