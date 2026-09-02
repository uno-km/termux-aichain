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
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { tool } from "../graph/agent.js";
const execFileAsync = promisify(execFile);
async function safeExec(cmd, args = [], timeout = 30000) {
    try {
        const { stdout } = await execFileAsync(cmd, args, { timeout });
        return stdout.trim();
    }
    catch (err) {
        throw new Error(`Command '${cmd} ${args.join(" ")}' failed: ${err.stderr || err.message}`);
    }
}
export const inferBitnetLlm = tool({
    name: "termux_bitnet_infer",
    description: "Invokes on-device 1.58-bit BitNet LLM engine for fast local text generation.",
    parameters: {
        type: "object",
        properties: {
            prompt: { type: "string", description: "Input prompt for BitNet LLM" },
            max_tokens: { type: "integer", description: "Maximum tokens to generate (default: 128)" }
        },
        required: ["prompt"]
    }
}, async (args) => {
    const prompt = args?.prompt ?? "";
    const maxTokens = args?.max_tokens ?? 128;
    try {
        return await safeExec("termux-bitnet", ["--prompt", prompt, "--n-predict", String(maxTokens)], 45000);
    }
    catch (err) {
        return JSON.stringify({
            error: "BITNET_INFERENCE_FAILED",
            message: err.message
        });
    }
});
export const transcribeSpeech = tool({
    name: "termux_stt_transcribe",
    description: "Transcribes live microphone audio or audio files to text using local device STT engine.",
    parameters: {
        type: "object",
        properties: {
            audio_path: { type: "string", description: "Optional WAV audio file path" },
            duration_sec: { type: "integer", description: "Recording duration in seconds (default: 5)" }
        },
        required: []
    }
}, async (args) => {
    const duration = args?.duration_sec ?? 5;
    const cmdArgs = args?.audio_path ? ["--input", args.audio_path] : ["--duration", String(duration)];
    try {
        return await safeExec("termux-stt", cmdArgs, (duration + 15) * 1000);
    }
    catch (err) {
        return JSON.stringify({
            error: "TRANSCRIPTION_FAILED",
            message: err.message
        });
    }
});
export const generateDiffusionImage = tool({
    name: "termux_diffusion_generate",
    description: "Generates an image from a text prompt using available mobile device resources (CPU/GPU).",
    parameters: {
        type: "object",
        properties: {
            prompt: { type: "string", description: "Text description for image generation" },
            output_path: { type: "string", description: "Target image file path (default: /tmp/output.png)" }
        },
        required: ["prompt"]
    }
}, async (args) => {
    const prompt = args?.prompt ?? "";
    const outPath = args?.output_path ?? "/tmp/output.png";
    try {
        return await safeExec("termux-diffusion", ["--prompt", prompt, "--output", outPath], 60000);
    }
    catch (err) {
        return JSON.stringify({
            error: "IMAGE_GENERATION_FAILED",
            message: err.message
        });
    }
});
export const browseWebHeadless = tool({
    name: "termux_playwright_browse",
    description: "Automates headless mobile web browser to extract text content or search results from target URL.",
    parameters: {
        type: "object",
        properties: {
            url: { type: "string", description: "Target HTTP/HTTPS URL" },
            query: { type: "string", description: "Search query or target CSS selector" }
        },
        required: ["url"]
    }
}, async (args) => {
    const url = args?.url ?? "";
    const cmdArgs = ["--url", url];
    if (args?.query)
        cmdArgs.push("--query", args.query);
    try {
        return await safeExec("termux-playwright", cmdArgs, 30000);
    }
    catch (err) {
        return JSON.stringify({
            error: "BROWSE_FAILED",
            message: err.message
        });
    }
});
export const synthesizeSpeech = tool({
    name: "termux_tts_synth",
    description: "Synthesizes text into high-quality WAV audio file using on-device DSP or ONNX neural vocoder.",
    parameters: {
        type: "object",
        properties: {
            text: { type: "string", description: "Input text to synthesize into speech" },
            output_path: { type: "string", description: "Target audio WAV output file path (default: /tmp/output.wav)" },
            lang: { type: "string", description: "Language code: 'ko' (Korean) or 'en' (English) (default: ko)" },
            speed: { type: "number", description: "Speech speed multiplier between 0.5 and 2.0 (default: 1.0)" },
            engine: { type: "string", description: "Synthesis engine: 'auto', 'dsp', or 'onnx' (default: auto)" }
        },
        required: ["text"]
    }
}, async (args) => {
    const text = args?.text ?? "";
    const outPath = args?.output_path ?? "/tmp/output.wav";
    const lang = args?.lang ?? "ko";
    const speed = String(args?.speed ?? 1.0);
    const engine = args?.engine ?? "auto";
    const cmdArgs = ["synth", "-t", text, "-o", outPath, "-l", lang, "-s", speed, "-e", engine];
    try {
        return await safeExec("termux-tts", cmdArgs, 45000);
    }
    catch (err) {
        return JSON.stringify({
            error: "TTS_SYNTHESIS_FAILED",
            message: err.message
        });
    }
});
export const speakText = tool({
    name: "termux_tts_speak",
    description: "Speaks text aloud directly through Android native speaker output.",
    parameters: {
        type: "object",
        properties: {
            text: { type: "string", description: "Input text to speak aloud" },
            lang: { type: "string", description: "Language code (default: ko)" },
            stream: { type: "string", description: "Audio stream: 'MUSIC', 'NOTIFICATION', or 'ALARM' (default: MUSIC)" }
        },
        required: ["text"]
    }
}, async (args) => {
    const text = args?.text ?? "";
    const lang = args?.lang ?? "ko";
    const stream = args?.stream ?? "MUSIC";
    const cmdArgs = ["speak", "-t", text, "-l", lang, "-s", stream];
    try {
        return await safeExec("termux-tts", cmdArgs, 30000);
    }
    catch (err) {
        return JSON.stringify({
            error: "TTS_SPEAK_FAILED",
            message: err.message
        });
    }
});
export const analyzeImageVlm = tool({
    name: "termux_vision_vlm",
    description: "Analyzes and describes an image or answers questions about an image using on-device Vision-Language Model (VLM).",
    parameters: {
        type: "object",
        properties: {
            image_path: { type: "string", description: "Target image file path (PNG/JPEG)" },
            prompt: { type: "string", description: "Text query or prompt asking about the image (default: 'Describe this image in detail.')" },
            model: { type: "string", description: "Optional model ID or custom .gguf path" }
        },
        required: ["image_path"]
    }
}, async (args) => {
    const imgPath = args?.image_path ?? "";
    const prompt = args?.prompt ?? "Describe this image in detail.";
    const cmdArgs = ["vlm", imgPath, "-p", prompt];
    if (args?.model)
        cmdArgs.push("-m", args.model);
    try {
        return await safeExec("termux-vision", cmdArgs, 60000);
    }
    catch (err) {
        return JSON.stringify({
            error: "VISION_VLM_FAILED",
            message: err.message
        });
    }
});
export const detectFaces = tool({
    name: "termux_vision_detect_face",
    description: "Detects faces in an image using on-device Haar cascade detector and extracts the cropped face.",
    parameters: {
        type: "object",
        properties: {
            image_path: { type: "string", description: "Target input image file path" },
            output_path: { type: "string", description: "Target output file path for cropped face (default: /tmp/face_crop.jpg)" }
        },
        required: ["image_path"]
    }
}, async (args) => {
    const imgPath = args?.image_path ?? "";
    const outPath = args?.output_path ?? "/tmp/face_crop.jpg";
    const cmdArgs = ["detect-face", imgPath, "-o", outPath];
    try {
        return await safeExec("termux-vision", cmdArgs, 30000);
    }
    catch (err) {
        return JSON.stringify({
            error: "VISION_FACE_DETECT_FAILED",
            message: err.message
        });
    }
});
export const detectEdgesCanny = tool({
    name: "termux_vision_canny",
    description: "Applies on-device 5-stage Canny Edge Detection to an image.",
    parameters: {
        type: "object",
        properties: {
            image_path: { type: "string", description: "Target input image file path" },
            output_path: { type: "string", description: "Target output file path for edge image (default: /tmp/edges.png)" },
            low: { type: "number", description: "Low hysteresis threshold (default: 40.0)" },
            high: { type: "number", description: "High hysteresis threshold (default: 120.0)" }
        },
        required: ["image_path"]
    }
}, async (args) => {
    const imgPath = args?.image_path ?? "";
    const outPath = args?.output_path ?? "/tmp/edges.png";
    const low = String(args?.low ?? 40.0);
    const high = String(args?.high ?? 120.0);
    const cmdArgs = ["canny", imgPath, "-o", outPath, "--low", low, "--high", high];
    try {
        return await safeExec("termux-vision", cmdArgs, 30000);
    }
    catch (err) {
        return JSON.stringify({
            error: "VISION_CANNY_FAILED",
            message: err.message
        });
    }
});
export function getEcosystemTools() {
    return [
        inferBitnetLlm,
        transcribeSpeech,
        generateDiffusionImage,
        browseWebHeadless,
        synthesizeSpeech,
        speakText,
        analyzeImageVlm,
        detectFaces,
        detectEdgesCanny
    ];
}
