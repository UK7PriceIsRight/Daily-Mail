# Health Weight Widget — Setup Guide

Scriptable does **not** have direct HealthKit access. This solution uses an
Apple Shortcut to read your weight from the Health app and save it to a JSON
file that the Scriptable widget reads.

## Architecture

```
Apple Health ──▶ Shortcut (reads weight) ──▶ JSON file ──▶ Scriptable widget
```

---

## Step 1 — Create the Apple Shortcut

Open the **Shortcuts** app and create a new shortcut named
**"Export Weight"** with the following actions in order:

### Action 1: Find Health Samples
- **Type:** Weight
- **Sort By:** Start Date
- **Order:** Latest First
- **Limit:** 1

When you add this action, iOS will prompt you to grant the shortcut access
to read Weight data from Health. Approve it.

### Action 2: Get Details of Health Sample
- Get **Value** of *Health Samples* (from step 1)
- Store or note this; it will be referenced as `Value`.

### Action 3: Get Details of Health Sample (again)
- Get **Start Date** of *Health Samples* (from step 1)
- Store or note this; it will be referenced as `Start Date`.

### Action 4: Text
Create a Text action with exactly this content (use the magic variable
tokens for Value and Start Date):

```
{"weight": [Value], "unit": "kg", "date": "[Start Date]"}
```

Replace `"kg"` with `"lbs"` if your Health app stores weight in pounds.

### Action 5: Save File
- **Save** the Text from step 4
- **Destination:** iCloud Drive
- **Path:** `Shortcuts/HealthWeight/weight.json`
- **Overwrite if exists:** ON

Run the shortcut once manually to create the folder and confirm it works.

---

## Step 2 — Automate the Shortcut

In the **Shortcuts** app, go to the **Automation** tab:

1. Tap **+** → **Create Personal Automation**
2. Choose **Time of Day**
3. Set it to run at intervals you prefer (e.g. every hour, or 3x/day)
4. Action: **Run Shortcut** → select "Export Weight"
5. Turn **off** "Ask Before Running" so it runs silently

This keeps the JSON file up to date automatically.

---

## Step 3 — Install the Scriptable Widget

1. Copy `HealthWeightWidget.js` into the **Scriptable** app:
   - Open Scriptable → tap **+** → paste the full script
   - Or place the `.js` file in the `Scriptable` folder on iCloud Drive
2. Run the script once inside Scriptable to verify it shows your weight.

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
| `PREFERRED_UNIT` | `"kg"` | Display unit: `"kg"` or `"lbs"` (auto-converts) |

---

## Troubleshooting

### Widget shows "No data found"
- Run the "Export Weight" shortcut manually and check that
  `iCloud Drive/Shortcuts/HealthWeight/weight.json` exists and contains
  valid JSON.
- Make sure the Scriptable app has iCloud Drive access enabled.

### Shortcut fails to read Health data
- Go to **Settings → Health → Data Access & Devices** and confirm your
  shortcut has permission to read Weight.
- Verify you have at least one weight entry in the Health app.

### Weight shows wrong number
- Check that the `"unit"` field in the JSON matches what your Health app
  actually uses (`"kg"` vs `"lbs"`).
- The widget auto-converts between units, so set `PREFERRED_UNIT` in the
  script to your desired display unit.

### Widget not updating
- Widgets refresh on iOS's schedule (roughly every 15–30 minutes).
- Ensure the Shortcuts automation is not paused or set to "Ask Before
  Running".
