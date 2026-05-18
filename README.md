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
