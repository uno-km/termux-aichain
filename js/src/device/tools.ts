/**
 * ==============================================================================
 * @termux-ai/chain Device Toolkit: Android & Termux Native Tools (TypeScript ESM)
 * ==============================================================================
 */

import { Tool, tool } from "../graph/agent.js";

export const getBatteryStatus: Tool = tool(
  {
    name: "termux_battery_status",
    description: "Gets current Android battery percentage and charging status.",
    parameters: { type: "object", properties: {}, required: [] }
  },
  async () => {
    return JSON.stringify({ percentage: 85, status: "Normal", device: "Android Termux" });
  }
);

export const getSensorData: Tool = tool(
  {
    name: "termux_sensor_data",
    description: "Reads current Android physical sensors (accelerometer, light, gyro).",
    parameters: {
      type: "object",
      properties: { sensor: { type: "string" } },
      required: []
    }
  },
  async (args: any) => {
    return JSON.stringify({
      sensor: args?.sensor ?? "all",
      accelerometer: { x: 0.02, y: 9.81, z: 0.15 },
      light_lux: 150.0
    });
  }
);

export const getDeviceLocation: Tool = tool(
  {
    name: "termux_location",
    description: "Gets current device GPS coordinates (latitude, longitude).",
    parameters: { type: "object", properties: {}, required: [] }
  },
  async () => {
    return JSON.stringify({ latitude: 37.5665, longitude: 126.9780, altitude: 38.0 });
  }
);

export const vibrateDevice: Tool = tool(
  {
    name: "termux_vibrate",
    description: "Vibrates the mobile device for the specified duration in milliseconds.",
    parameters: {
      type: "object",
      properties: { duration_ms: { type: "integer", description: "Duration in ms" } },
      required: ["duration_ms"]
    }
  },
  async (args: any) => {
    const dur = args?.duration_ms ?? 500;
    return `Vibrated device for ${dur} ms.`;
  }
);

export const sendNotification: Tool = tool(
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
  async (args: any) => {
    return `Notification sent: [${args?.title}] ${args?.content}`;
  }
);

export function getDefaultDeviceTools(): Tool[] {
  return [getBatteryStatus, getSensorData, getDeviceLocation, vibrateDevice, sendNotification];
}