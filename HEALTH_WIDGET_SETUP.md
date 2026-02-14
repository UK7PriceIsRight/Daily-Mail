# Health Weight Widget — Setup Guide

Scriptable does **not** have direct HealthKit access. This solution uses an
Apple Shortcut to read your weight from the Health app and pass it to a small
Scriptable helper script (`SaveWeight.js`) that writes the JSON file the
widget reads.

## Architecture

```
Apple Health ──▶ Shortcut ──▶ SaveWeight.js (writes weight.json) ──▶ Widget
```

---

## Step 1 — Add Scripts to Scriptable

Copy **both** scripts into the Scriptable app:

1. **SaveWeight.js** — the helper that receives weight from the Shortcut and
   writes `weight.json`.
2. **HealthWeightWidget.js** — the widget that reads `weight.json` and
   displays your weight.

For each script: open Scriptable → tap **+** → paste the full contents →
name it exactly `SaveWeight` and `HealthWeightWidget`.

---

## Step 2 — Create the Apple Shortcut

Open the **Shortcuts** app and create a new shortcut named
**"Export Weight"** with the following actions in order:

### Action 1: Find Health Samples
- **Type:** Weight
- **Sort By:** Start Date
- **Order:** Latest First
- **Limit:** 1

When you add this action, iOS will prompt you to grant the shortcut access
to read Weight data from Health. Approve it.

### Action 2: Run Script
- **App:** Scriptable
- **Script:** SaveWeight
- **Input:** tap "Input" → choose **Shortcut Input**, then tap the blue
  "Shortcut Input" pill and change it to **Health Samples** (the result
  from Action 1)

That's it — only two actions. No Text action, no Save File action.
Scriptable handles writing the JSON file itself, which avoids the problems
with Shortcuts variable substitution and file-saving permissions.

Run the shortcut once manually. You should see a confirmation like
"Saved: 186.7 lbs" as the output.

---

## Step 3 — Automate the Shortcut

In the **Shortcuts** app, go to the **Automation** tab:

1. Tap **+** → **Create Personal Automation**
2. Choose **Time of Day**
3. Set it to run at intervals you prefer (e.g. every hour, or 3x/day)
4. Action: **Run Shortcut** → select "Export Weight"
5. Turn **off** "Ask Before Running" so it runs silently

This keeps the JSON file up to date automatically.

---

## Step 4 — Add the Home Screen Widget

1. Long-press your Home Screen → tap **+** (top-left)
2. Search for **Scriptable**
3. Select the **Small** widget size → Add Widget
4. Long-press the new widget → **Edit Widget**
5. Set **Script** to `HealthWeightWidget`
6. Done

---

## Configuration

In `HealthWeightWidget.js`, you can change:

| Variable | Default | Description |
|---|---|---|
| `PREFERRED_UNIT` | `"lbs"` | Display unit: `"kg"` or `"lbs"` (auto-converts) |

In `SaveWeight.js`, you can change:

| Variable | Default | Description |
|---|---|---|
| `unit` (in the data object) | `"lbs"` | Unit your Health app stores weight in |

---

## Troubleshooting

### Widget shows "No data found"
- Run the "Export Weight" shortcut manually and check the output message.
- Open Scriptable → tap SaveWeight → Run to verify `weight.json` exists.

### Shortcut shows "Error: no input received"
- Make sure Action 2 has its **Input** set to **Health Samples** (the
  output of Action 1), not "Ask Each Time" or blank.

### Shortcut shows "Error: could not parse weight"
- This means the Health Sample value couldn't be read as a number.
- Verify you have at least one weight entry in the Health app.

### Shortcut fails to read Health data
- Go to **Settings → Health → Data Access & Devices** and confirm your
  shortcut has permission to read Weight.
- Verify you have at least one weight entry in the Health app.

### Weight shows wrong number
- Check that the `unit` field in `SaveWeight.js` matches what your Health
  app actually uses (`"kg"` vs `"lbs"`).
- The widget auto-converts between units, so set `PREFERRED_UNIT` in the
  widget script to your desired display unit.

### Widget not updating
- Widgets refresh on iOS's schedule (roughly every 15–30 minutes).
- Ensure the Shortcuts automation is not paused or set to "Ask Before
  Running".
