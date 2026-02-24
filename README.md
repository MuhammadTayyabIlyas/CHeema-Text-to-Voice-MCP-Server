# Cheema Text-to-Voice MCP Server

> An MCP (Model Context Protocol) server that brings **AI-powered text-to-speech** into **Claude Desktop**, **Claude Code**, **n8n**, and any MCP-compatible platform. Powered by [NeuTTS](https://github.com/neuphonic/neutts) — state-of-the-art, open-source, on-device TTS with instant voice cloning. Supports **stdio**, **SSE**, and **HTTP** transports.

[![MCP](https://img.shields.io/badge/MCP-Compatible-blue?style=for-the-badge&logo=anthropic)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![NeuTTS](https://img.shields.io/badge/NeuTTS-Powered-orange?style=for-the-badge)](https://github.com/neuphonic/neutts)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

---

## What Is This?

This project lets you generate speech directly from your AI assistant. Just ask Claude to "say something" and it will synthesize a WAV file using any of the built-in voices — or your own cloned voice.

### Key Features

- **5 MCP tools** — synthesize speech, list speakers, list models, add custom voices, help guide
- **2 MCP prompts** — pre-built templates for quick speech and voice cloning
- **Multi-transport** — stdio (CLI), SSE (n8n/web), and streamable-http
- **5 built-in voices** — English (dave, jo), German (greta), French (juliette), Spanish (mateo)
- **Instant voice cloning** — register any voice from a 3-15 second WAV sample
- **Multilingual** — English, German, French, Spanish (model-dependent)
- **Runs locally** — no API keys, no cloud, full privacy
- **AI-friendly onboarding** — rich instructions and a `tts_help` tool guide any AI agent
- **Thread-safe** — concurrent requests handled safely

---

## MCP Tools

| Tool | Parameters | Description |
|------|-----------|-------------|
| `tts_help` | *none* | Get a complete usage guide with examples — call this first! |
| `tts_synthesize` | `text` (required), `speaker` (default: `"jo"`), `output_filename` (optional) | Convert text to speech, saves WAV to output directory |
| `tts_list_speakers` | *none* | List all available speaker voices with language and source |
| `tts_list_models` | *none* | List available NeuTTS backbone models, show currently loaded model |
| `tts_add_speaker` | `name`, `wav_path`, `ref_text`, `language` (default: `"en-us"`) | Register a new voice from a WAV audio file |

## MCP Prompts (Pre-built Templates)

| Prompt | Parameters | Description |
|--------|-----------|-------------|
| `quick_speech` | `text` (required), `speaker` (optional, default: `"jo"`) | Generate speech quickly with a single prompt |
| `voice_clone_guide` | *none* | Step-by-step walkthrough for cloning a new voice |

These show up automatically in Claude Desktop's prompt picker and in n8n's MCP prompt list.

---

## Quick Start

### Prerequisites

- **Python 3.10+**
- **espeak-ng** (system dependency for phonemization)

```bash
# Ubuntu/Debian
sudo apt install espeak-ng

# macOS
brew install espeak-ng

# Windows
choco install espeak-ng
```

### 1. Clone & Install

```bash
git clone https://github.com/MuhammadTayyabIlyas/CHeema-Text-to-Voice-MCP-Server.git
cd CHeema-Text-to-Voice-MCP-Server

# Create virtual environment and install dependencies
python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate          # Windows

pip install -e .
pip install "mcp[cli]"
```

### 2. Register with Claude Code

```bash
claude mcp add cheema-tts -- /path/to/CHeema-Text-to-Voice-MCP-Server/venv/bin/python /path/to/CHeema-Text-to-Voice-MCP-Server/mcp_server.py
```

For example, if you cloned into your home directory:

```bash
claude mcp add cheema-tts -- ~/CHeema-Text-to-Voice-MCP-Server/venv/bin/python ~/CHeema-Text-to-Voice-MCP-Server/mcp_server.py
```

### 3. Register with Claude Desktop

Add this to your Claude Desktop config file:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "cheema-tts": {
      "command": "/path/to/CHeema-Text-to-Voice-MCP-Server/venv/bin/python",
      "args": ["/path/to/CHeema-Text-to-Voice-MCP-Server/mcp_server.py"],
      "env": {}
    }
  }
}
```

### 4. Use It

Once registered, just ask Claude naturally:

> "Convert this text to speech: Hello, welcome to the Cheema Text-to-Voice server!"

> "List available speakers"

> "Say 'Good morning everyone' using the dave voice"

> "Add my voice as a new speaker from /path/to/my_voice.wav"

---

## Configuration

The server is configured via environment variables. All are optional with sensible defaults:

| Variable | Default | Description |
|----------|---------|-------------|
| `NEUTTS_BACKBONE` | `neuphonic/neutts-nano` | HuggingFace backbone model repo |
| `NEUTTS_BACKBONE_DEVICE` | `cpu` | Device for backbone (`cpu` or `cuda`) |
| `NEUTTS_CODEC` | `neuphonic/neucodec` | HuggingFace codec model repo |
| `NEUTTS_CODEC_DEVICE` | `cpu` | Device for codec (`cpu` or `cuda`) |
| `NEUTTS_OUTPUT_DIR` | `./output` | Directory for generated WAV files |
| `NEUTTS_SAMPLES_DIR` | `./samples` | Directory for built-in speaker samples |
| `NEUTTS_SPEAKERS_DIR` | `./speakers` | Directory for custom speaker data |
| `NEUTTS_TRANSPORT` | `stdio` | MCP transport: `stdio`, `sse`, or `streamable-http` |
| `NEUTTS_HOST` | `127.0.0.1` | Host to bind for SSE/HTTP transports |
| `NEUTTS_PORT` | `8000` | Port to bind for SSE/HTTP transports |

### Example with Environment Variables

```bash
NEUTTS_BACKBONE="neuphonic/neutts-air" NEUTTS_BACKBONE_DEVICE="cuda" \
  claude mcp add cheema-tts -- /path/to/venv/bin/python /path/to/mcp_server.py
```

Or in Claude Desktop config:

```json
{
  "mcpServers": {
    "cheema-tts": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/mcp_server.py"],
      "env": {
        "NEUTTS_BACKBONE": "neuphonic/neutts-air",
        "NEUTTS_BACKBONE_DEVICE": "cuda"
      }
    }
  }
}
```

---

## Transport Options

The server supports three transports. Choose based on your platform:

| Transport | Flag | Use Case | Default |
|-----------|------|----------|---------|
| `stdio` | `--transport stdio` | Claude Code, Claude Desktop (local pipe) | Yes |
| `sse` | `--transport sse` | n8n, web dashboards, remote clients | No |
| `streamable-http` | `--transport streamable-http` | HTTP-based MCP clients | No |

Environment variables: `NEUTTS_TRANSPORT`, `NEUTTS_HOST`, `NEUTTS_PORT`

```bash
# stdio (default) — used by Claude Code / Claude Desktop
python mcp_server.py

# SSE — used by n8n and web platforms
python mcp_server.py --transport sse --host 0.0.0.0 --port 8000

# Streamable HTTP
python mcp_server.py --transport streamable-http --host 0.0.0.0 --port 8000
```

---

## Production Deployment (audio.pakedx.com)

The server runs in production on **server2** (`82.223.44.124`) behind Nginx with HTTPS.

### Architecture

```
MCP Client ──HTTPS──▶ Nginx (audio.pakedx.com:443) ──HTTP──▶ MCP Server (127.0.0.1:8765)
```

### Endpoints

| Client | URL |
|--------|-----|
| n8n (local on server2) | `http://127.0.0.1:8765/sse` |
| n8n (external) | `https://audio.pakedx.com/sse` |
| Claude Desktop | `https://audio.pakedx.com/sse` |
| Any MCP client | `https://audio.pakedx.com/sse` |

### Systemd Service

The server runs as `cheema-tts.service` — auto-starts on boot, auto-restarts on crash.

```bash
# Status / logs
systemctl status cheema-tts
journalctl -u cheema-tts -f

# Restart
systemctl restart cheema-tts
```

Service file: `/etc/systemd/system/cheema-tts.service`

### Nginx Config

Config: `/etc/nginx/sites-available/audio.pakedx.com`

Key settings for SSE:
- `proxy_buffering off` — required for SSE streaming
- `proxy_cache off` / `X-Accel-Buffering: no` — prevent response caching
- `proxy_read_timeout 86400` — SSE connections are long-lived (24h)
- `proxy_set_header Host $proxy_host` — backend rejects non-localhost Host headers

SSL managed by Let's Encrypt (certbot auto-renewal).

### Server Paths

| Path | Description |
|------|-------------|
| `/var/www/voice/neutts/` | Project root |
| `/var/www/voice/venv/` | Python 3.12.3 virtual environment |
| `/var/www/voice/neutts/output/` | Generated WAV files |
| `/var/www/voice/neutts/samples/` | Built-in speaker samples |
| `/var/www/voice/neutts/speakers/` | Custom speaker data |

---

## n8n Setup

### On the Same Server (server2)

n8n on server2 connects directly — no Nginx/SSL overhead:

1. Add an **MCP Client Tool** node (or AI Agent with MCP tool)
2. Set connection type: **SSE**
3. URL: `http://127.0.0.1:8765/sse`

### From an External n8n Instance

1. Add an **MCP Client Tool** node
2. Set connection type: **SSE**
3. URL: `https://audio.pakedx.com/sse`

### Available Tools via n8n

- **tts_list_speakers** — discover available voices
- **tts_synthesize** — generate speech (returns JSON with WAV file path and duration)
- **tts_add_speaker** — clone a new voice
- **tts_help** — get the full usage guide

---

## Other MCP Platforms

Any MCP-compatible platform can connect:

| Transport | Endpoint |
|-----------|----------|
| SSE (production) | `https://audio.pakedx.com/sse` |
| SSE (local) | `http://127.0.0.1:8765/sse` |
| stdio (CLI) | `python mcp_server.py` |
| streamable-http | `python mcp_server.py --transport streamable-http` |

### Claude Desktop Config

```json
{
  "mcpServers": {
    "cheema-tts": {
      "url": "https://audio.pakedx.com/sse"
    }
  }
}
```


---

## Available Models

| Model | Language | Size | Cloning |
|-------|----------|------|---------|
| `neuphonic/neutts-air` | English | ~552M params | Yes |
| `neuphonic/neutts-air-q4-gguf` | English | Q4 quantized | Yes |
| `neuphonic/neutts-air-q8-gguf` | English | Q8 quantized | Yes |
| `neuphonic/neutts-nano` | English | ~229M params | Yes |
| `neuphonic/neutts-nano-q4-gguf` | English | Q4 quantized | Yes |
| `neuphonic/neutts-nano-q8-gguf` | English | Q8 quantized | Yes |
| `neuphonic/neutts-nano-german` | German | ~229M params | Yes |
| `neuphonic/neutts-nano-french` | French | ~229M params | Yes |
| `neuphonic/neutts-nano-spanish` | Spanish | ~229M params | Yes |

Use `tts_list_models` to see the full list and currently active model.

---

## Built-in Speakers

| Speaker | Language | Description |
|---------|----------|-------------|
| `jo` | English (en-us) | Default voice — clear, natural English |
| `dave` | English (en-us) | Male English voice |
| `greta` | German (de) | German voice |
| `juliette` | French (fr-fr) | French voice |
| `mateo` | Spanish (es) | Spanish voice |

---

## Adding Custom Voices

You can clone any voice with just a short audio sample:

1. **Prepare a WAV file** — 3 to 15 seconds of clean, natural speech
2. **Know the transcript** — the exact text spoken in the WAV file
3. **Use the `tts_add_speaker` tool**:

```
Add a new speaker called "myvoice" from /path/to/recording.wav
with the transcript "This is what I said in the recording"
```

Custom voices are persisted in the `speakers/` directory and survive server restarts.

### Voice Cloning Tips

For best results, reference audio should be:

- **Mono channel** audio
- **16-44 kHz** sample rate
- **3-15 seconds** in length
- **Clean** — minimal background noise
- **Natural speech** — continuous, conversational tone

---

## Project Structure

```
CHeema-Text-to-Voice-MCP-Server/
├── mcp_server.py          # The MCP server (main file)
├── neutts/                # NeuTTS engine source
├── samples/               # Built-in speaker samples (.wav, .pt, .txt)
│   ├── jo.wav / jo.pt / jo.txt
│   ├── dave.wav / dave.pt / dave.txt
│   ├── greta.wav / greta.pt / greta.txt
│   ├── juliette.wav / juliette.pt / juliette.txt
│   └── mateo.wav / mateo.pt / mateo.txt
├── speakers/              # Custom speaker data (auto-created)
│   └── speakers.json      # Custom speaker registry
├── output/                # Generated WAV files (auto-created)
├── examples/              # NeuTTS usage examples
└── README.md
```

---

## Troubleshooting

### Server won't start

- Make sure `espeak-ng` is installed: `espeak-ng --version`
- Verify the venv has all dependencies: `pip list | grep -E "mcp|neutts|torch|soundfile"`
- Check stderr output for model loading errors

### No audio output

- Check the `output/` directory for generated WAV files
- Verify the speaker name is valid with `tts_list_speakers`

### Slow first run

The first run downloads model weights from HuggingFace (~200MB-500MB depending on model). Subsequent runs use cached models.

### CUDA/GPU support

Set `NEUTTS_BACKBONE_DEVICE=cuda` and `NEUTTS_CODEC_DEVICE=cuda` for GPU acceleration. Requires PyTorch with CUDA support.

---

## How It Works

1. On startup, the server loads the NeuTTS backbone model and codec
2. Pre-encoded speaker references (`.pt` files) are loaded into memory
3. When `tts_synthesize` is called, the text is phonemized, combined with the speaker's reference codes, and fed through the model
4. The model generates speech tokens which are decoded by the codec into a waveform
5. The waveform is saved as a 24kHz WAV file
6. All stdout from NeuTTS is redirected to stderr to protect the MCP JSON-RPC transport

---

## Credits

- **NeuTTS Engine** by [Neuphonic](https://neuphonic.com/) — the underlying TTS model
- **MCP Protocol** by [Anthropic](https://anthropic.com/) — the communication standard

---

## Author

**Tayyab Ilyas** — PhD Researcher & EdTech Founder

Building AI-powered tools for educators and researchers.

[![Website](https://img.shields.io/badge/Website-tayyabcheema.com-blue?style=flat-square&logo=google-chrome&logoColor=white)](https://tayyabcheema.com)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-tayyabcheema777-0A66C2?style=flat-square&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/tayyabcheema777/)
[![GitHub](https://img.shields.io/badge/GitHub-tayyabcheema-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/tayyabcheema)
[![Twitter](https://img.shields.io/badge/Twitter-@tayyabcheema777-1DA1F2?style=flat-square&logo=twitter&logoColor=white)](https://x.com/tayyabcheema777)
[![YouTube](https://img.shields.io/badge/YouTube-TayyabCheema-FF0000?style=flat-square&logo=youtube&logoColor=white)](https://www.youtube.com/@TayyabCheema)
[![Google Scholar](https://img.shields.io/badge/Google_Scholar-Profile-4285F4?style=flat-square&logo=google-scholar&logoColor=white)](https://scholar.google.com/citations?user=z5OLA2sAAAAJ&hl=en)
[![ORCID](https://img.shields.io/badge/ORCID-0000--0002--5381--1996-A6CE39?style=flat-square&logo=orcid&logoColor=white)](https://orcid.org/0000-0002-5381-1996)

---

## License

This project is licensed under the MIT License. The underlying NeuTTS models have their own licenses — see the [NeuTTS repository](https://github.com/neuphonic/neutts) for details.

---

<p align="center">
  <strong>Cheema Text-to-Voice MCP Server</strong><br>
  Give your AI assistant a voice.
</p>
