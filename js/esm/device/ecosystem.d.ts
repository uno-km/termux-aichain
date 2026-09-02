/**
 * ==============================================================================
 * @termux-ai/chain Device Ecosystem: Integrations with uno-km Edge Projects (TS ESM)
 * ==============================================================================
 * Provides standard Tool interfaces for uno-km sovereign edge modules:
 * - termux-bitnet (1.58-bit On-Device LLM)
 * - termux-stt (Speech-to-Text)
 * - termux-diffusion (Device Resource-based Image Generation)
 * - termux-playwright (Headless Browser Automation)
 * - termux-tts (DSP / ONNX Neural & Native Voice Synthesis)
 * - termux-vision (On-Device Computer Vision & VLM Multimodal Engine)
 * Zero external heavy dependencies - Pure Node.js 18+ standard library.
 */
import { Tool } from "../graph/agent.js";
export declare const inferBitnetLlm: Tool;
export declare const transcribeSpeech: Tool;
export declare const generateDiffusionImage: Tool;
export declare const browseWebHeadless: Tool;
export declare const synthesizeSpeech: Tool;
export declare const speakText: Tool;
export declare const analyzeImageVlm: Tool;
export declare const detectFaces: Tool;
export declare const detectEdgesCanny: Tool;
export declare function getEcosystemTools(): Tool[];
