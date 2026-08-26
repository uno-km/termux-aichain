import test from "node:test";
import assert from "node:assert";
import { getDefaultDeviceTools, getBatteryStatus } from "../js/esm/device/tools.js";

test("Node.js: Device tools default suite", async () => {
  const tools = getDefaultDeviceTools();
  assert.strictEqual(tools.length, 3);
  assert.strictEqual(tools[0].name, "termux_battery_status");

  const batRes = await tools[0].func();
  const parsed = JSON.parse(batRes);
  assert.ok("percentage" in parsed);
});