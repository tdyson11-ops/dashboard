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

## Fuel (nutrition log)

`nutrition.html` is a tap-to-log calorie/protein tracker (linked from the dashboard and training log):

- Daily targets (3,200 kcal / 160g protein) with color-coded progress
- Pre-loaded staple foods — tap once to log, tap +/− to adjust quantity
- Custom foods can be logged once or saved as new staples ("Edit staples" to remove)
- 7-day view with daily totals and average
- Same localStorage + Export/Import backup model as the training log

## Side hustle

`hustle.html` is a standalone **Hustle** app (linked from the dashboard) for running one
specific business to £1,000/month: **AI-written local content for independent gyms and PT
studios, £250 per client per month.** Four clients is the target.

The split that makes it work: **the robot writes, you decide.** Content production —
the part that would otherwise eat a day a month per client — is fully automated. Cold
emails are never sent automatically and client posts are never published live
automatically, because both are irreversible and outward-facing.

### The app

- **MRR to £1,000**, with how many clients are still missing and roughly how many emails that means
- **Today's 20 minutes** — a short queue that changes with the stage you're at
- **Pipeline** — tap ± on leads → samples → replies → calls → clients; it shows the conversion rate between each step so you can see which stage is actually broken
- **Clients**, **the robot's last run**, the offer, a six-week plan and the tax/PECR notes

Pipeline counts and plan ticks live in localStorage and sync across devices. Everything
else comes from `hustle.json`.

### The engine

`hustle_engine.py` has two modes, both driven by the `Side Hustle` workflow:

| Mode | Runs | What it does |
|---|---|---|
| `outreach` | Weekdays 7am | For each lead marked `new`: writes a real 900-word article *for that specific business* plus a personalised cold email. Lands in `outbox/` as a workflow artifact |
| `deliver` | 1st of the month, 8am | For each active client: plans the month, then writes 4 blog posts, 12 social captions, 4 Google Business posts and a newsletter into `clients/<slug>/<YYYY-MM>/` |

The free sample is the whole pitch — it's a real article they can publish whether or not
they ever reply, which is why it has to be good rather than a teaser.

Run either by hand from the Actions tab (**Side Hustle → Run workflow**) to test.

### Setup

| Secret | Needed for | Value |
|---|---|---|
| `ANTHROPIC_API_KEY` | Both | From the [Anthropic console](https://console.anthropic.com). Runs cost roughly 20p per client per month |
| `LEADS_CSV` | Outreach | The lead list, pasted in whole (see below) |
| `LEADS_WRITE_TOKEN` | Outreach | Optional. A PAT with `secrets: write` so the workflow can save lead statuses back. Without it the same leads regenerate each run |

**The lead list never goes in the repo** — it holds names and email addresses. It lives in
the `LEADS_CSV` secret and is written to disk only for the length of a run; `outbox/` is
gitignored and comes back as an artifact you download. Columns:

```csv
business,contact,email,town,website,focus,status,notes
Iron Works Gym,Dave,dave@ironworks.co.uk,Macclesfield,ironworks.co.uk,strength training and small-group PT,new,
```

Only rows with `status` of `new` are picked up, four per run.

### Adding a client

Add an entry to `clients` in `hustle.json` (the app has a **Copy a blank client entry**
button). `town` and `focus` are what the engine writes from, so they need to be real:

```json
{
  "name": "Iron Works Gym", "slug": "iron-works-gym",
  "town": "Macclesfield", "focus": "strength training and small-group PT",
  "price": 250, "status": "active",
  "wordpress_url": "https://ironworks.co.uk"
}
```

Set `wordpress_url` plus `WP_<SLUG>_USER` and `WP_<SLUG>_APP_PASSWORD` secrets (slug
uppercased, hyphens as underscores) and posts go straight into their site — **as drafts**,
so nothing appears on a client's site without a human pressing publish. Change
`publish_status` to `"publish"` per client once you trust it.

### Before you start

- **UK trading allowance is £1,000 per tax year.** You'll pass it in month one — register as a sole trader with HMRC when you do.
- **Cold email under PECR:** fine to a registered company with an opt-out in every message; sole traders and partnerships count as individuals and need consent. Only email limited companies, and honour removals permanently.
- **Get client sign-off in writing** before anything is published live.

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
