import test from "node:test";
import assert from "node:assert";
import { getDefaultDeviceTools, getBatteryStatus, getSensorData } from "../js/esm/device/tools.js";

test("Node.js: Device tools default suite", async () => {
  const tools = getDefaultDeviceTools();
  assert.strictEqual(tools.length, 5);
  assert.strictEqual(tools[0].name, "termux_battery_status");

  const batRes = await tools[0].func();
  const parsed = JSON.parse(batRes);
  assert.ok("percentage" in parsed || "error" in parsed);

  const sensorRes = await tools[1].func({ sensor: "accel" });
  const parsedSensor = JSON.parse(sensorRes);
  assert.ok("accelerometer" in parsedSensor || "error" in parsedSensor);
});