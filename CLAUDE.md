# Working with Tom on this repo

## How to explain things

When the answer involves a calculation, an estimate, or a multi-step setup,
**give the method as numbered bullets showing each step and its number**, not
just the conclusion. Tom wants to see how the figure was reached so he can
redo it himself with different inputs.

Good:
- Target is £1,000/month
- Each client pays £250 → 1,000 ÷ 250 = **4 clients**
- About 1 in 25 emails becomes a client → 4 × 25 = **100 emails**

Bad: "You'll need about 100 emails."

Say plainly when a number is an estimate rather than a fact, and what it
depends on.

## The apps

Mobile-first PWAs on GitHub Pages, all in the same idiom: dark theme, 430px
max width, Inter, `--accent: #f59e0b`. Data comes from a JSON file in the
repo; user edits live in localStorage and sync to Firestore via `sync.js`.
Any new localStorage key must be added to `SYNC_KEYS` there.

Automation is GitHub Actions cron → Python (stdlib + `requests`/`anthropic`)
→ JSON committed back to the repo.

## Rules that matter

- Nothing outward-facing happens without a human step. The hustle engine
  writes cold emails but never sends them, and writes client posts as drafts
  but never publishes them.
- Personal data (the lead list, outreach drafts) stays out of the repo — it
  lives in GitHub secrets and workflow artifacts. See `.gitignore`.
- Prefer adding to an existing app over creating a new one.
