// Variables used by Scriptable.
// These must be at the very top of the file. Do not edit.
// icon-color: red; icon-glyph: heartbeat;

/**
 * SaveWeight — Helper script called by the Apple Shortcut.
 *
 * The Shortcut passes the latest Health weight sample as input.
 * This script extracts the numeric value, builds the JSON, and
 * writes weight.json to Scriptable's local documents folder
 * (where HealthWeightWidget.js reads it).
 *
 * SHORTCUT SETUP (only 2 actions needed):
 *   1. "Find Health Samples" — Type: Weight, Sort: Latest First, Limit: 1
 *   2. "Run Script" — Script: SaveWeight, Input: Health Samples
 */

const fm = FileManager.local();
const path = fm.joinPath(fm.documentsDirectory(), "weight.json");

// Get the weight value passed from the Shortcut
const input = args.shortcutParameter;

if (input == null) {
  // Running directly in Scriptable (not from a Shortcut) — show status
  if (fm.fileExists(path)) {
    const existing = JSON.parse(fm.readString(path));
    const alert = new Alert();
    alert.title = "SaveWeight";
    alert.message = "Last saved: " + existing.weight.toFixed(1) + " " + existing.unit + "\n" + existing.date + "\n\nThis script is meant to be run from the Export Weight shortcut, not directly.";
    alert.addAction("OK");
    await alert.present();
  } else {
    const alert = new Alert();
    alert.title = "SaveWeight";
    alert.message = "No weight.json found yet.\n\nRun this script from the Export Weight shortcut (not directly). The shortcut passes your Health weight data as input.";
    alert.addAction("OK");
    await alert.present();
  }
  Script.complete();
  return;
}

// Parse the weight value — Shortcuts may pass a number, string, or dict
let weightValue;

if (typeof input === "number") {
  weightValue = input;
} else if (typeof input === "string") {
  weightValue = parseFloat(input);
} else if (typeof input === "object" && input.value != null) {
  // Health Sample dict sometimes has a .value property
  weightValue = parseFloat(input.value);
} else if (typeof input === "object" && input.weight != null) {
  weightValue = parseFloat(input.weight);
} else {
  // Try converting whatever we got
  weightValue = parseFloat(String(input));
}

if (isNaN(weightValue)) {
  Script.setShortcutOutput("Error: could not parse weight from input: " + JSON.stringify(input));
  Script.complete();
  throw new Error("Could not parse weight value");
}

// Build the data object
const data = {
  weight: weightValue,
  unit: "lbs",
  date: new Date().toISOString()
};

// Write to disk
fm.writeString(path, JSON.stringify(data));

// Return confirmation to the Shortcut
Script.setShortcutOutput("Saved: " + data.weight.toFixed(1) + " " + data.unit);
Script.complete();
