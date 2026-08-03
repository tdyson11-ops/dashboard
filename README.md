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
- Each day shows calories and protein against the daily target (**3,200 kcal / 190 g protein** — edit `TARGET` at the top of `mealdata.js` to change; Fuel reads its own `FUEL_TARGET`, keep the two in step)
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

## Fuel (nutrition log)

`nutrition.html` is a tap-to-log calorie/protein tracker (linked from the dashboard and training log):

- Daily targets (3,200 kcal / 190g protein) with color-coded progress
- **Today's plan** — the meals planned for today in the Meal planner, each logged with one tap, or
  **Log the whole day** for all of them at once. Already-logged meals show a ✓ and can't be double-logged
- **Log a meal** — any recipe from the planner's library (plus your own saved meals), grouped by
  Breakfast/Lunch/Dinner/Snack; the group matching the time of day opens by default
- **Extras & ingredients** — the original staple foods for single items on top of meals; +/− adjusts quantity
- Custom foods can be logged once or saved as new staples ("Edit staples" to remove)
- 7-day view with daily totals and average
- Same localStorage + Export/Import backup model as the training log

Meals read the shared recipe library and weekly plan (`mealdata.js`, `meal-plan-v1`, `meal-custom-v1`),
so a cooked meal is one tap instead of re-entering its ingredients. If `mealdata.js` is unavailable the
meal sections simply don't render and the food log still works.

> Targets are **3,200 kcal / 190 g protein** across both apps. They're declared in two places —
> `FUEL_TARGET` in `nutrition.html` and `TARGET` in `mealdata.js` — so change both together.

## Cross-device sync

`sync.js` mirrors the apps' data to a Firebase (Firestore) project so logging on one device
shows up on every device. Loaded by the Dashboard, Fuel, Meal planner, Shopping and Training apps
(the Dashboard syncs its Site/Pillar notes and habit ticks).

- Sign in once per device via the sync bar at the bottom of any app; the session is remembered
- The apps keep working entirely from localStorage — sync just keeps a cloud copy in step
- The cloud copy is the source of truth: on a fresh device, sign in and it pulls your data down.
  Sign in on the device that already holds your data **first** — it seeds the cloud
- `persist.js` additionally asks the browser to keep each app's local storage from being evicted
- Firebase web config lives in `sync.js` (public by design). Auth uses Email/Password; Firestore
  rules restrict every document to its owner:

  ```
  rules_version = '2';
  service cloud.firestore {
    match /databases/{database}/documents {
      match /users/{uid}/{document=**} {
        allow read, write: if request.auth != null && request.auth.uid == uid;
      }
    }
  }
  ```

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

Tap **↻** in the dashboard header to pull the latest `data.json` without closing the app. It re-renders
the WHOOP numbers and every `data.json`-driven section, stamps the header with the time it checked, and
clears the service-worker cache so a new deploy is picked up. Locally-stored things (focus, habit ticks,
notes) are untouched, and if you're offline it says so and leaves the current data on screen.

### data.json fields

| Field | What to update |
|---|---|
| `updated` | Date string shown at the top |
| `focus` | Array of priority tasks — **seeds** the editable Today's Focus list on first load |
| `whoop.recovery` | Recovery % from WHOOP app (0–100) |
| `whoop.hrv` | HRV in ms |
| `whoop.rhr` | Resting heart rate in bpm |
| `whoop.sleep_score` | Sleep score % |
| `whoop.strain` | Day strain score |
| `university.deadlines` | Array of `{ name, module, date }` — `date` is ISO `YYYY-MM-DD`. Sorted soonest-first, badge turns red inside 7 days. Empty array hides the list |
| `university.modules` | Array of `{ name, term, progress }` — `progress` is 0–100 |
| `habits` | Array of daily habit names — tap to tick on the dashboard (ticks stored per device in localStorage) |
| `pillars` | Array of `{ name, status }` — status: `ticking`, `ontrack`, or `atrisk` |
| `goals` | Array of `{ name, status }` — status text drives the pill colour (`At risk` = amber, `Done` = green, else neutral) |
| `site_notes` | Array of `{ name, tag }` — **seeds** the editable Site Notes on first load |
| `pillar_notes` | Array of `{ icon, name }` — **seeds** the editable Pillar Notes on first load (`icon` is an emoji) |

The **Command Center** components mirror the Notion dashboard. Pillars, Goals, Uni modules and
submission deadlines are edited via `data.json`.

Edited directly on the dashboard (no `data.json` needed):

- **Today's Focus** — tap an item to edit it, the box to tick it off, **+ Add focus** to add,
  **Clear done** to sweep finished ones
- **Site Notes** / **Pillar Notes** — tap to edit title, tag/emoji and body; **+ Add note** / delete
- **Habits** — tap to tick. The card shows a **30-day average** (share of habit boxes ticked, measured
  from your first logged day in the window so the weeks before you started don't count against you),
  a current streak of all-ticked days, and a 7-day strip

Focus, notes and habit ticks are stored in the browser's localStorage and **synced across devices**
when signed in via the sync bar (see Cross-device sync above) — `data.json` only provides the initial
content the first time the page loads on a device. The **Backup** card at the bottom also lets you
**Export**/**Import** them as a JSON file for an offline safety net.
