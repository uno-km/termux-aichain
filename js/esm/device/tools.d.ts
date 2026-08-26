/**
 * ==============================================================================
 * @termux-ai/chain Device Toolkit: Android & Termux Native Tools (TypeScript ESM)
 * ==============================================================================
 */
import { Tool } from "../graph/agent.js";
export declare const getBatteryStatus: Tool;
export declare const getSensorData: Tool;
export declare const getDeviceLocation: Tool;
export declare const vibrateDevice: Tool;
export declare const sendNotification: Tool;
export declare function getDefaultDeviceTools(): Tool[];
