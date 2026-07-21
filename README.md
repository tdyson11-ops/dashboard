# Tom Dyson — Personal Dashboard

Mobile-first personal dashboard hosted on GitHub Pages.

## Setup (one-time)

1. Create a new GitHub repo — name it `dashboard` (or anything you like)
2. Push this folder to it:
   ```
   cd C:\Users\ThomasDyson\dashboard
   git init
   git add .
   git commit -m "Initial dashboard"
   git remote add origin https://github.com/YOUR-USERNAME/dashboard.git
   git push -u origin main
   ```
3. In the repo on GitHub: **Settings → Pages → Source → main / root → Save**
4. Your dashboard will be live at `https://YOUR-USERNAME.github.io/dashboard/`

Add it to your phone's home screen: open the URL in Safari/Chrome, then **Share → Add to Home Screen**.

## Training log

`training.html` is a standalone training tracker (linked from the main dashboard):

- Pre-loaded 4-day upper/lower program + 2 cardio days, with the shoulder primer on every session
- Logs sets/reps/weights, shows last session's numbers as placeholders and flags when to add weight
- Tracks the 3 weekly metrics: 7-day average body weight (and kg/week rate), weekly training volume vs last week, and shoulder pain score
- Data is stored in the browser's localStorage **on the device you log with** — use the Export button every week or two to download a JSON backup (Import restores it)

## Fuel (nutrition log)

`nutrition.html` is a tap-to-log calorie/protein tracker (linked from the dashboard and training log):

- Daily targets (3,200 kcal / 160g protein) with color-coded progress
- Pre-loaded staple foods — tap once to log, tap +/− to adjust quantity
- Custom foods can be logged once or saved as new staples ("Edit staples" to remove)
- 7-day view with daily totals and average
- Same localStorage + Export/Import backup model as the training log

## WHOOP auto-update

The `Update WHOOP Data` workflow refreshes `data.json` daily. WHOOP refresh tokens are
**single-use** — every refresh returns a new token — so the workflow persists the current
token in `.whoop_token.enc`, encrypted with the `WHOOP_TOKEN_KEY` secret, and commits it
back to the repo. The `WHOOP_REFRESH_TOKEN` secret only seeds the first run.

Required repo secrets (Settings → Secrets and variables → Actions):

| Secret | Value |
|---|---|
| `WHOOP_CLIENT_ID` | From the WHOOP developer dashboard |
| `WHOOP_CLIENT_SECRET` | From the WHOOP developer dashboard |
| `WHOOP_REFRESH_TOKEN` | Fresh token from `python get_token.py <id> <secret>` |
| `WHOOP_TOKEN_KEY` | Any long random string (encrypts the rotated token) |

If the workflow ever fails with all tokens rejected: re-run `get_token.py`, update the
`WHOOP_REFRESH_TOKEN` secret, and delete `.whoop_token.enc` from the repo.

## Updating data

Edit `data.json` and push to GitHub — the dashboard updates within ~60 seconds.

Or edit it directly on GitHub.com (pencil icon) for quick updates from your phone.

### data.json fields

| Field | What to update |
|---|---|
| `updated` | Date string shown at the top |
| `focus` | Array of 1–4 priority tasks for the day |
| `whoop.recovery` | Recovery % from WHOOP app (0–100) |
| `whoop.hrv` | HRV in ms |
| `whoop.rhr` | Resting heart rate in bpm |
| `whoop.sleep_score` | Sleep score % |
| `whoop.strain` | Day strain score |
| `cyden.plots_complete` | Units complete |
| `cyden.plots_total` | Total units on scheme |
| `cyden.current_stage` | Current active stage description |
| `cyden.next_milestone` | Next key milestone and date |
| `cyden.kpis` | Array of KPIs — status: `green`, `amber`, or `red` |
| `university.module` | Current module name |
| `university.next_deadline` | ISO date: `YYYY-MM-DD` |
| `university.deadline_label` | Short label for the deadline |
| `university.grade_target` | Target grade |
| `university.current_avg` | Current module average |
