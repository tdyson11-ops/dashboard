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

## Meal planner

`meals.html` is a standalone, Mise-style weekly meal planner (linked from the main dashboard):

- Plan Breakfast / Lunch / Dinner / Snack across the seven days of the week, tapping any slot to pick from the recipe library
- Recipe library is built for the **72 → 77 kg lean bulk** on the training page — high-protein, high-calorie meals a personal trainer would recommend, each with macros, ingredients and a quick method
- **Auto-plan week** fills the whole week with a varied, batch-friendly high-protein rotation in one tap
- Each day shows calories and protein against the daily target (default **3000 kcal / 190 g protein** — edit `TARGET` at the top of the script to change)
- **Log your own meal** on any slot — enter a name, portion/weight note and macros for anything cooked for you or eaten off-plan. Logged meals count toward the day's macros but are **not** added to the shopping list; tick "Save to My meals" to reuse recurring ones (e.g. a parent's regular dinner)
- Tap **🛒 Morrisons shopping list** to jump to the Shopping app (below)
- Like the training log, the plan lives in the browser's localStorage **on the device you use** — use Export for a JSON backup (Import restores it)

Add it to your home screen the same way as the dashboard (**Share → Add to Home Screen**) and it installs as its own **Meals** app.

## Shopping list

`shopping.html` is a standalone, installable **Shopping** app driven by whatever you set in the meal planner:

- Aggregates every ingredient across the planned week, combines duplicates (e.g. all the milk becomes one line) and groups them by Morrisons store aisle — Fruit & Veg, Meat & Poultry, Fish, Dairy, Bakery, Food Cupboard — in the order you walk the shop
- **Tick items off** as you shop (the ticks persist); **Copy list** puts a plain-text version on the clipboard; **Reset ticks** clears them for next time
- Meals you logged yourself are left off — it only lists the recipes you're actually cooking
- Plan on Sunday/Monday night in the Meals app, then open the Shopping app in store — it re-reads the plan automatically. Add it to your home screen for its own **Shopping** icon
- The recipe library, targets and aisle map are shared with the meal planner in **`mealdata.js`** (single source of truth — add or edit recipes there and both apps update)

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
