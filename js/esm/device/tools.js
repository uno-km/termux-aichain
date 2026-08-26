/**
 * ==============================================================================
 * @termux-ai/chain Device Toolkit: Android & Termux Native Tools (Node.js ESM)
 * ==============================================================================
 * Zero fake simulation strings - 100% Ground Truth native execution & diagnostics.
 */
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import fs from "node:fs";
import { tool } from "../graph/agent.js";

const execFileAsync = promisify(execFile);

async function safeExec(cmd, args = [], timeout = 3000) {
  try {
    const { stdout } = await execFileAsync(cmd, args, { timeout });
    return stdout.trim();
  } catch {
    return null;
  }
}

export const getBatteryStatus = tool(
  {
    name: "termux_battery_status",
    description: "Gets current Android battery percentage and charging status.",
    parameters: { type: "object", properties: {}, required: [] }
  },
  async () => {
    // 1. Try termux-battery-status CLI
    const termuxRes = await safeExec("termux-battery-status");
    if (termuxRes) {
      try {
        JSON.parse(termuxRes);
        return termuxRes;
      } catch {}
    }

    // 2. Kernel sysfs fallback
    const capPath = "/sys/class/power_supply/battery/capacity";
    const statPath = "/sys/class/power_supply/battery/status";
    if (fs.existsSync(capPath)) {
      try {
        const cap = parseInt(fs.readFileSync(capPath, "utf-8").trim(), 10);
        let stat = "Discharging";
        if (fs.existsSync(statPath)) {
          stat = fs.readFileSync(statPath, "utf-8").trim();
        }
        return JSON.stringify({ percentage: cap, status: stat, source: "kernel_sysfs" });
      } catch {}
    }

    return JSON.stringify({
      error: "BATTERY_DATA_UNAVAILABLE",
      message: "Neither termux-battery-status nor kernel sysfs /sys/class/power_supply/battery is accessible."
    });
  }
);

export const getSensorData = tool(
  {
    name: "termux_sensor_data",
    description: "Reads current Android physical sensors (accelerometer, light, gyro).",
    parameters: {
      type: "object",
      properties: { sensor: { type: "string", description: "Sensor type: 'all', 'accel', 'light'" } },
      required: []
    }
  },
  async (args) => {
    const sensorType = args?.sensor ?? "all";
    const cmdArgs = ["-n", "1"];
    if (sensorType !== "all") cmdArgs.push("-s", sensorType);
    const res = await safeExec("termux-sensor", cmdArgs, 3000);
    if (res) return res;

    return JSON.stringify({
      error: "SENSOR_UNAVAILABLE",
      message: "termux-sensor is not available or timed out. Install termux-api and grant sensor permissions."
    });
  }
);

export const getDeviceLocation = tool(
  {
    name: "termux_location",
    description: "Gets current device GPS coordinates (latitude, longitude).",
    parameters: {
      type: "object",
      properties: { provider: { type: "string", description: "Location provider: 'gps', 'network', 'last'" } },
      required: []
    }
  },
  async (args) => {
    const prov = args?.provider ?? "last";
    const res = await safeExec("termux-location", ["-p", prov, "-r", "last"], 4000);
    if (res) return res;

    return JSON.stringify({
      error: "LOCATION_UNAVAILABLE",
      message: "termux-location is not available. Install termux-api and enable location permissions."
    });
  }
);

export const vibrateDevice = tool(
  {
    name: "termux_vibrate",
    description: "Vibrates the mobile device for the specified duration in milliseconds.",
    parameters: {
      type: "object",
      properties: { duration_ms: { type: "integer", description: "Duration in ms" } },
      required: ["duration_ms"]
    }
  },
  async (args) => {
    const dur = args?.duration_ms ?? 500;
    const res = await safeExec("termux-vibrate", ["-d", String(dur)]);
    if (res !== null) {
      return JSON.stringify({ status: "SUCCESS", message: `Vibrated device for ${dur} ms.` });
    }
    return JSON.stringify({
      error: "VIBRATE_UNAVAILABLE",
      message: "termux-vibrate command not found. Install termux-api to enable haptic feedback."
    });
  }
);

export const sendNotification = tool(
  {
    name: "termux_notification",
    description: "Shows a native Android status bar notification with a title and content.",
    parameters: {
      type: "object",
      properties: {
        title: { type: "string" },
        content: { type: "string" }
      },
      required: ["title", "content"]
    }
  },
  async (args) => {
    const title = args?.title ?? "Notification";
    const content = args?.content ?? "";
    const res = await safeExec("termux-notification", ["--title", String(title), "--content", String(content)]);
    if (res !== null) {
      return JSON.stringify({ status: "SUCCESS", message: `Notification displayed: [${title}] ${content}` });
    }
    return JSON.stringify({
      error: "NOTIFICATION_UNAVAILABLE",
      message: "termux-notification not found. Install termux-api to enable notifications."
    });
  }
);

export function getDefaultDeviceTools() {
  return [getBatteryStatus, getSensorData, getDeviceLocation, vibrateDevice, sendNotification];
}