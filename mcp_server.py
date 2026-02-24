#!/usr/bin/env python3
"""Cheema Text-to-Voice MCP Server — exposes NeuTTS text-to-speech via Model Context Protocol.

Author: Tayyab Ilyas (https://tayyabcheema.com)
Repository: https://github.com/MuhammadTayyabIlyas/CHeema-Text-to-Voice-MCP-Server
License: MIT
"""

import contextlib
import json
import os
import sys
import threading
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Instructions shown to every connecting AI agent
# ---------------------------------------------------------------------------
INSTRUCTIONS = """
Cheema Text-to-Voice MCP Server — AI-powered text-to-speech with voice cloning.

QUICK START:
1. Call tts_list_speakers to see available voices
2. Call tts_synthesize with your text to generate speech
3. Call tts_add_speaker to clone a new voice from a WAV file

AVAILABLE TOOLS:
- tts_help          → Get detailed usage guide and examples (start here!)
- tts_list_speakers → List voices (dave, jo, greta, juliette, mateo + custom)
- tts_list_models   → Show loaded model and alternatives
- tts_synthesize    → Convert text to speech WAV file
- tts_add_speaker   → Clone a new voice from audio sample

EXAMPLE:
  tts_synthesize(text="Hello world!", speaker="jo")

PROMPTS (pre-built templates):
- quick_speech      → Fast speech generation with just text
- voice_clone_guide → Step-by-step voice cloning walkthrough
"""

# ---------------------------------------------------------------------------
# Configuration via environment variables
# ---------------------------------------------------------------------------
NEUTTS_DIR = Path(__file__).resolve().parent
BACKBONE = os.environ.get("NEUTTS_BACKBONE", "neuphonic/neutts-nano")
BACKBONE_DEVICE = os.environ.get("NEUTTS_BACKBONE_DEVICE", "cpu")
CODEC = os.environ.get("NEUTTS_CODEC", "neuphonic/neucodec")
CODEC_DEVICE = os.environ.get("NEUTTS_CODEC_DEVICE", "cpu")
OUTPUT_DIR = Path(os.environ.get("NEUTTS_OUTPUT_DIR", NEUTTS_DIR / "output"))
SAMPLES_DIR = Path(os.environ.get("NEUTTS_SAMPLES_DIR", NEUTTS_DIR / "samples"))
SPEAKERS_DIR = Path(os.environ.get("NEUTTS_SPEAKERS_DIR", NEUTTS_DIR / "speakers"))

# ---------------------------------------------------------------------------
# Ensure directories exist
# ---------------------------------------------------------------------------
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SPEAKERS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Built-in speakers and their languages (for reference)
# ---------------------------------------------------------------------------
BUILTIN_SPEAKERS = {
    "dave": {"language": "en-us"},
    "jo": {"language": "en-us"},
    "greta": {"language": "de"},
    "juliette": {"language": "fr-fr"},
    "mateo": {"language": "es"},
}

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
tts = None
speakers: dict[str, dict] = {}  # name -> {ref_codes, ref_text, language, source}
infer_lock = threading.Lock()


def _load_model():
    """Load the NeuTTS model, redirecting stdout to stderr to protect JSON-RPC."""
    global tts
    # NeuTTS prints progress to stdout — redirect so we don't corrupt stdio transport
    with contextlib.redirect_stdout(sys.stderr):
        from neutts import NeuTTS as _NeuTTS

        tts = _NeuTTS(
            backbone_repo=BACKBONE,
            backbone_device=BACKBONE_DEVICE,
            codec_repo=CODEC,
            codec_device=CODEC_DEVICE,
        )


def _load_builtin_speakers():
    """Pre-load built-in speakers from the samples directory."""
    for name, meta in BUILTIN_SPEAKERS.items():
        pt_path = SAMPLES_DIR / f"{name}.pt"
        txt_path = SAMPLES_DIR / f"{name}.txt"
        wav_path = SAMPLES_DIR / f"{name}.wav"

        if not txt_path.exists():
            print(f"[cheema-tts] WARNING: missing {txt_path}, skipping {name}", file=sys.stderr)
            continue

        ref_text = txt_path.read_text().strip()

        # Prefer pre-encoded .pt file, fall back to encoding from .wav
        if pt_path.exists():
            ref_codes = torch.load(pt_path, weights_only=True)
        elif wav_path.exists():
            with contextlib.redirect_stdout(sys.stderr):
                ref_codes = tts.encode_reference(str(wav_path))
            torch.save(ref_codes, pt_path)
        else:
            print(f"[cheema-tts] WARNING: no audio for {name}, skipping", file=sys.stderr)
            continue

        speakers[name] = {
            "ref_codes": ref_codes,
            "ref_text": ref_text,
            "language": meta["language"],
            "source": "builtin",
        }

    print(f"[cheema-tts] Loaded {len(speakers)} built-in speakers", file=sys.stderr)


def _load_custom_speakers():
    """Load custom speakers from speakers/speakers.json."""
    registry_path = SPEAKERS_DIR / "speakers.json"
    if not registry_path.exists():
        return

    with open(registry_path) as f:
        registry = json.load(f)

    for name, meta in registry.items():
        pt_path = SPEAKERS_DIR / f"{name}.pt"
        if not pt_path.exists():
            print(f"[cheema-tts] WARNING: missing {pt_path}, skipping custom speaker {name}", file=sys.stderr)
            continue

        ref_codes = torch.load(pt_path, weights_only=True)
        speakers[name] = {
            "ref_codes": ref_codes,
            "ref_text": meta["ref_text"],
            "language": meta.get("language", "en-us"),
            "source": "custom",
        }

    print(f"[cheema-tts] Loaded {len(registry)} custom speaker(s)", file=sys.stderr)


def _save_custom_registry():
    """Persist the custom speakers registry to speakers.json."""
    registry = {}
    for name, data in speakers.items():
        if data["source"] == "custom":
            registry[name] = {
                "ref_text": data["ref_text"],
                "language": data["language"],
            }
    with open(SPEAKERS_DIR / "speakers.json", "w") as f:
        json.dump(registry, f, indent=2)


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "Cheema Text-to-Voice",
    instructions=INSTRUCTIONS,
)


@mcp.tool()
def tts_help() -> str:
    """Get started with Cheema Text-to-Voice. Returns a complete usage guide
    with examples for all tools. Call this first if you're new!"""
    return """
=== Cheema Text-to-Voice — Quick Start Guide ===

STEP 1: See available voices
  → Call tts_list_speakers()
  Returns JSON with voice names, languages, and whether they are built-in or custom.

STEP 2: Generate speech
  → Call tts_synthesize(text="Your text here", speaker="jo")
  Parameters:
    - text (required): The text to speak
    - speaker (optional, default "jo"): Voice name from tts_list_speakers
    - output_filename (optional): Custom WAV filename; auto-generated if omitted
  Returns JSON with output_path, duration_seconds, speaker, and sample_rate.

STEP 3: Clone a new voice
  → Call tts_add_speaker(name="myvoice", wav_path="/path/to/sample.wav",
                         ref_text="Exact words in the sample", language="en-us")
  Requirements:
    - WAV file: 3-15 seconds of clean speech, mono, 16-44 kHz
    - ref_text: Exact transcript of what is spoken in the WAV
  The new voice is saved and available immediately.

OTHER TOOLS:
  → tts_list_models(): See the currently loaded NeuTTS backbone model and alternatives.

AUDIO TIPS:
  - Output is always 24 kHz mono WAV
  - For non-English voices, use the matching speaker (greta=German, juliette=French, mateo=Spanish)
  - Custom voices persist across server restarts

TROUBLESHOOTING:
  - "Unknown speaker" → call tts_list_speakers to see valid names
  - Slow first run → model weights are downloading from HuggingFace (one-time)
  - No audio file → check the output_path in the JSON response
"""


@mcp.tool()
def tts_list_speakers() -> str:
    """List all available speaker voices.

    Returns a JSON object mapping speaker names to their metadata
    (language, source: builtin/custom).
    """
    result = {}
    for name, data in speakers.items():
        result[name] = {
            "language": data["language"],
            "source": data["source"],
        }
    return json.dumps(result, indent=2)


@mcp.tool()
def tts_list_models() -> str:
    """List available NeuTTS backbone models and show which one is currently loaded.

    Returns a JSON object with 'current' (the active model) and 'available'
    (all known model repo IDs).
    """
    from neutts.neutts import BACKBONE_LANGUAGE_MAP

    available = list(BACKBONE_LANGUAGE_MAP.keys())
    return json.dumps(
        {"current": BACKBONE, "available": available},
        indent=2,
    )


@mcp.tool()
def tts_synthesize(text: str, speaker: str = "jo", output_filename: str = "") -> str:
    """Convert text to speech using a specified speaker voice.

    Args:
        text: The text to convert to speech.
        speaker: Speaker voice name (default: "jo"). Use tts_list_speakers to see options.
        output_filename: Optional output WAV filename. Auto-generated if omitted.

    Returns a JSON object with the output file path and duration.
    """
    if speaker not in speakers:
        available = ", ".join(sorted(speakers.keys()))
        return json.dumps({"error": f"Unknown speaker '{speaker}'. Available: {available}"})

    spk = speakers[speaker]

    # Generate output filename if not provided
    if not output_filename:
        timestamp = int(time.time() * 1000)
        output_filename = f"{speaker}_{timestamp}.wav"

    if not output_filename.endswith(".wav"):
        output_filename += ".wav"

    output_path = OUTPUT_DIR / output_filename

    # Synthesize with stdout protection and thread safety
    with infer_lock, contextlib.redirect_stdout(sys.stderr):
        wav = tts.infer(text, spk["ref_codes"], spk["ref_text"])

    sf.write(str(output_path), wav, 24000)
    duration = len(wav) / 24000.0

    return json.dumps({
        "output_path": str(output_path),
        "duration_seconds": round(duration, 2),
        "speaker": speaker,
        "sample_rate": 24000,
    })


@mcp.tool()
def tts_add_speaker(name: str, wav_path: str, ref_text: str, language: str = "en-us") -> str:
    """Register a new speaker voice from a WAV audio file.

    Args:
        name: Unique name for the speaker.
        wav_path: Absolute path to a WAV file of the speaker's voice.
        ref_text: Transcript of what is said in the WAV file.
        language: Language code (default: "en-us"). Examples: "de", "fr-fr", "es".

    Returns confirmation with the registered speaker details.
    """
    if name in speakers and speakers[name]["source"] == "builtin":
        return json.dumps({"error": f"Cannot overwrite built-in speaker '{name}'."})

    wav_path_obj = Path(wav_path)
    if not wav_path_obj.exists():
        return json.dumps({"error": f"WAV file not found: {wav_path}"})

    # Encode the reference audio
    with contextlib.redirect_stdout(sys.stderr):
        ref_codes = tts.encode_reference(str(wav_path_obj))

    # Save the encoded reference
    pt_path = SPEAKERS_DIR / f"{name}.pt"
    torch.save(ref_codes, pt_path)

    # Register in memory
    speakers[name] = {
        "ref_codes": ref_codes,
        "ref_text": ref_text,
        "language": language,
        "source": "custom",
    }

    # Persist registry
    _save_custom_registry()

    return json.dumps({
        "name": name,
        "language": language,
        "ref_text": ref_text,
        "encoded_path": str(pt_path),
    })


# ---------------------------------------------------------------------------
# MCP Prompts (pre-built templates for AI agents)
# ---------------------------------------------------------------------------
@mcp.prompt()
def quick_speech(text: str, speaker: str = "jo") -> str:
    """Generate speech quickly. Provide text and an optional speaker name."""
    return (
        f'Please synthesize the following text as speech using the "{speaker}" voice:\n\n'
        f'"{text}"\n\n'
        "Use the tts_synthesize tool with the text and speaker above, "
        "then tell me the output file path and duration."
    )


@mcp.prompt()
def voice_clone_guide() -> str:
    """Step-by-step walkthrough for cloning a new voice."""
    return (
        "I'd like to clone a new voice. Please walk me through the process:\n\n"
        "1. First, list the current speakers with tts_list_speakers so I can see what exists.\n"
        "2. Then ask me for:\n"
        "   - A name for the new voice\n"
        "   - The path to a WAV file (3-15 sec, clean mono speech)\n"
        "   - The exact transcript of what is said in the WAV\n"
        "   - The language code (e.g. en-us, de, fr-fr, es)\n"
        "3. Use tts_add_speaker to register the voice.\n"
        "4. Finally, generate a short test sentence with the new voice using tts_synthesize."
    )


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
print("[cheema-tts] Initializing NeuTTS model...", file=sys.stderr)
_load_model()
_load_builtin_speakers()
_load_custom_speakers()
print("[cheema-tts] Server ready.", file=sys.stderr)

# ---------------------------------------------------------------------------
# Multi-transport support (stdio / sse / streamable-http)
# ---------------------------------------------------------------------------
TRANSPORT = os.environ.get("NEUTTS_TRANSPORT", "stdio")
HOST = os.environ.get("NEUTTS_HOST", "127.0.0.1")
PORT = int(os.environ.get("NEUTTS_PORT", "8000"))

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Cheema Text-to-Voice MCP Server")
    parser.add_argument(
        "--transport",
        default=TRANSPORT,
        choices=["stdio", "sse", "streamable-http"],
        help="MCP transport type (default: stdio)",
    )
    parser.add_argument("--host", default=HOST, help="Host to bind (SSE/HTTP, default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=PORT, help="Port to bind (SSE/HTTP, default: 8000)")
    args = parser.parse_args()

    mcp.settings.host = args.host
    mcp.settings.port = args.port
    mcp.run(transport=args.transport)
