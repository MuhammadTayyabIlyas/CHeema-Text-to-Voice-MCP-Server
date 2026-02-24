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
    description="Cheema Text-to-Voice MCP Server — synthesize speech, manage voices, powered by NeuTTS.",
)


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
# Startup
# ---------------------------------------------------------------------------
print("[cheema-tts] Initializing NeuTTS model...", file=sys.stderr)
_load_model()
_load_builtin_speakers()
_load_custom_speakers()
print("[cheema-tts] Server ready.", file=sys.stderr)

if __name__ == "__main__":
    mcp.run(transport="stdio")
