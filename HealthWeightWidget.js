// Variables used by Scriptable.
// These must be at the very top of the file. Do not edit.
// icon-color: deep-green; icon-glyph: weight;

/**
 * Health Weight Widget for Scriptable (iOS)
 *
 * IMPORTANT: Scriptable does NOT have direct HealthKit access.
 * This widget reads weight data from a JSON file that must be
 * written by an Apple Shortcut. See SETUP below.
 *
 * SETUP:
 * 1. Create an Apple Shortcut with these actions:
 *    a) "Find Health Samples" — Type: Weight, Sort by: Start Date,
 *       Order: Latest First, Limit: 1
 *    b) "Get Details of Health Sample" — get Value and Start Date
 *    c) "Text" — build a JSON string:
 *         {"weight": [Value], "unit": "lbs", "date": "[Start Date]"}
 *    d) "Save File" — save the text to:
 *         On My iPhone > Scriptable > weight.json
 *
 * 2. Create a Shortcuts Automation:
 *    Trigger: Time of Day (e.g. every hour, or several times/day)
 *    Action: Run the shortcut from step 1
 *
 * 3. Place this script in Scriptable and add it as a small widget.
 *
 * UNIT CONFIGURATION:
 * Change PREFERRED_UNIT below to "lbs" if you want pounds.
 * The shortcut should export in the unit your Health app uses.
 */

const PREFERRED_UNIT = "lbs"; // "kg" or "lbs"
const KG_TO_LBS = 2.20462;
const LBS_TO_KG = 0.453592;

// Path to the JSON file written by the Apple Shortcut.
// Default: On My iPhone > Scriptable > weight.json
const DATA_FILENAME = "weight.json";

async function loadWeightData() {
  // Try iCloud first (most common), then fall back to local
  const managers = [];
  try {
    const iCloud = FileManager.iCloud();
    managers.push(iCloud);
  } catch (e) {
    // iCloud not available
  }
  managers.push(FileManager.local());

  for (const fm of managers) {
    const filePath = fm.joinPath(fm.documentsDirectory(), DATA_FILENAME);

    if (!fm.fileExists(filePath)) continue;

    // If iCloud file, ensure it's downloaded
    if (fm !== FileManager.local() && !fm.isFileDownloaded(filePath)) {
      await fm.downloadFileFromiCloud(filePath);
    }

    const raw = fm.readString(filePath);
    if (!raw || raw.trim().length === 0) continue;

    try {
      return JSON.parse(raw);
    } catch (e) {
      console.error("Failed to parse weight data: " + e.message);
    }
  }

  return null;
}

function convertWeight(value, fromUnit, toUnit) {
  if (fromUnit === toUnit) return value;
  if (fromUnit === "kg" && toUnit === "lbs") return value * KG_TO_LBS;
  if (fromUnit === "lbs" && toUnit === "kg") return value * LBS_TO_KG;
  return value;
}

function formatWeight(value, unit) {
  return `${value.toFixed(1)} ${unit}`;
}

function formatTimestamp(dateString) {
  const date = new Date(dateString);
  if (isNaN(date.getTime())) {
    return dateString; // Return as-is if unparseable
  }

  const df = new DateFormatter();
  df.useShortDateStyle();
  df.useShortTimeStyle();
  return df.string(date);
}

function relativeTime(dateString) {
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return "";

  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return formatTimestamp(dateString);
}

async function createWidget(data) {
  const widget = new ListWidget();
  widget.setPadding(12, 14, 12, 14);

  // Background gradient
  const gradient = new LinearGradient();
  gradient.locations = [0, 1];
  gradient.colors = [
    new Color("#1a1a2e"),
    new Color("#16213e"),
  ];
  widget.backgroundGradient = gradient;

  if (!data) {
    // No data state
    const title = widget.addText("Weight");
    title.font = Font.semiboldSystemFont(14);
    title.textColor = Color.white();

    widget.addSpacer(6);

    const msg = widget.addText("No data found");
    msg.font = Font.systemFont(12);
    msg.textColor = Color.gray();

    widget.addSpacer(4);

    const hint = widget.addText("Run the Health\nShortcut first");
    hint.font = Font.systemFont(10);
    hint.textColor = new Color("#888888");
    hint.minimumScaleFactor = 0.7;

    return widget;
  }

  const sourceUnit = data.unit || "kg";
  const weightValue = convertWeight(data.weight, sourceUnit, PREFERRED_UNIT);

  // Header with SF Symbol
  const headerStack = widget.addStack();
  headerStack.layoutHorizontally();
  headerStack.centerAlignContent();

  const icon = headerStack.addImage(SFSymbol.named("heart.fill").image);
  icon.imageSize = new Size(12, 12);
  icon.tintColor = new Color("#e94560");

  headerStack.addSpacer(5);

  const title = headerStack.addText("Weight");
  title.font = Font.semiboldSystemFont(14);
  title.textColor = Color.white();

  widget.addSpacer(6);

  // Weight value
  const valueParts = formatWeight(weightValue, PREFERRED_UNIT).split(" ");
  const valueText = widget.addText(valueParts[0]);
  valueText.font = Font.boldMonospacedSystemFont(28);
  valueText.textColor = Color.white();
  valueText.minimumScaleFactor = 0.6;

  // Unit label
  const unitText = widget.addText(valueParts[1]);
  unitText.font = Font.mediumSystemFont(14);
  unitText.textColor = new Color("#aaaaaa");

  widget.addSpacer(null);

  // Timestamp
  const timeStr = relativeTime(data.date);
  const timeText = widget.addText(timeStr);
  timeText.font = Font.systemFont(10);
  timeText.textColor = new Color("#888888");
  timeText.minimumScaleFactor = 0.7;

  return widget;
}

// Main
const data = await loadWeightData();
const widget = await createWidget(data);

if (config.runsInWidget) {
  Script.setWidget(widget);
} else {
  // Preview in-app
  widget.presentSmall();
}

Script.complete();
