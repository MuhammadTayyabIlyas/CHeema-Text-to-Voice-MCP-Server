# Cheema Text-to-Voice MCP Server

> **Free, open-source text-to-speech for AI assistants.** Generate natural speech directly from Claude Desktop, Claude Code, n8n, or any MCP-compatible platform. No API keys. No cloud. Runs entirely on your machine.

[![MCP](https://img.shields.io/badge/MCP-Compatible-blue?style=for-the-badge&logo=anthropic)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![NeuTTS](https://img.shields.io/badge/NeuTTS-Powered-orange?style=for-the-badge)](https://github.com/neuphonic/neutts)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

---

## What Can It Do?

Just ask your AI assistant to speak — it handles the rest:

> *"Say hello in French using the juliette voice"*

> *"Convert this paragraph to speech and save it as intro.wav"*

> *"Clone my voice from this recording and use it to read my essay"*

**5 built-in voices** across 4 languages, plus **instant voice cloning** from a short audio sample.

---

## Quick Start

### 1. Install Prerequisites

You need **Python 3.10+** and **espeak-ng**:

```bash
# Ubuntu / Debian
sudo apt install espeak-ng

# macOS
brew install espeak-ng

# Windows
choco install espeak-ng
```

### 2. Clone & Install

```bash
git clone https://github.com/MuhammadTayyabIlyas/CHeema-Text-to-Voice-MCP-Server.git
cd CHeema-Text-to-Voice-MCP-Server

python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate          # Windows

pip install -e .
pip install "mcp[cli]"
```

### 3. Connect to Your AI Assistant

Pick your platform and follow the steps below.

---

## Setup by Platform

### Claude Desktop

Add this to your config file:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "cheema-tts": {
      "command": "/full/path/to/CHeema-Text-to-Voice-MCP-Server/venv/bin/python",
      "args": ["/full/path/to/CHeema-Text-to-Voice-MCP-Server/mcp_server.py"],
      "env": {}
    }
  }
}
```

Restart Claude Desktop. You'll see the TTS tools appear in the tools menu.

### Claude Code

```bash
claude mcp add cheema-tts -- /full/path/to/venv/bin/python /full/path/to/mcp_server.py
```

Then just ask Claude to generate speech in any conversation.

### n8n

Start the server in SSE mode:

```bash
cd CHeema-Text-to-Voice-MCP-Server
source venv/bin/activate
python mcp_server.py --transport sse --host 127.0.0.1 --port 8000
```

In your n8n workflow:

1. Add an **AI Agent** node with an **MCP Client Tool**
2. Set connection type to **SSE**
3. Enter the URL: `http://127.0.0.1:8000/sse`
4. The agent can now call any TTS tool

### Any Other MCP Client

Start the server with your preferred transport:

```bash
# SSE (for web platforms and remote clients)
python mcp_server.py --transport sse --host 0.0.0.0 --port 8000

# Streamable HTTP
python mcp_server.py --transport streamable-http --host 0.0.0.0 --port 8000
```

Connect your MCP client to:
- **SSE**: `http://<your-host>:8000/sse`
- **HTTP**: `http://<your-host>:8000/mcp`

---

## Available Voices

| Voice | Language | Description |
|-------|----------|-------------|
| **jo** | English | Default — clear, natural female voice |
| **dave** | English | Male voice |
| **greta** | German | German female voice |
| **juliette** | French | French female voice |
| **mateo** | Spanish | Spanish male voice |

Use `tts_list_speakers` to see all voices including any custom ones you've added.

---

## Voice Cloning

Clone any voice from a short audio sample:

1. **Record or find a WAV file** — 3 to 15 seconds of clean speech
2. **Know the transcript** — the exact words spoken in the recording
3. **Ask your AI assistant**:

> *"Add a new speaker called 'alex' from /path/to/recording.wav — the transcript is 'This is what I said in the recording'"*

Or call the tool directly:

```
tts_add_speaker(name="alex", wav_path="/path/to/recording.wav", ref_text="This is what I said in the recording")
```

Custom voices are saved permanently and available across restarts.

**Tips for best results:**
- Mono audio, 16-44 kHz sample rate
- 3-15 seconds of continuous, natural speech
- Minimal background noise

---

## Available Tools

| Tool | What It Does |
|------|-------------|
| `tts_help` | Shows a complete usage guide with examples — **start here** |
| `tts_synthesize` | Converts text to speech, saves a WAV file |
| `tts_list_speakers` | Lists all available voices |
| `tts_list_models` | Shows the active model and alternatives |
| `tts_add_speaker` | Clones a new voice from an audio sample |

### tts_synthesize Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `text` | Yes | — | The text to convert to speech |
| `speaker` | No | `"jo"` | Which voice to use |
| `output_filename` | No | auto-generated | Custom filename for the WAV output |

### MCP Prompts (Templates)

| Prompt | Description |
|--------|-------------|
| `quick_speech` | Fast speech generation — just provide text and optional speaker |
| `voice_clone_guide` | Step-by-step walkthrough for adding a new voice |

These appear automatically in Claude Desktop's prompt picker.

---

## Models

The default model (`neutts-nano`) works great on CPU. Larger models produce higher quality but need more resources.

| Model | Language | Size | Notes |
|-------|----------|------|-------|
| `neuphonic/neutts-nano` | English | ~229M | **Default** — fast, good quality |
| `neuphonic/neutts-air` | English | ~552M | Higher quality, slower |
| `neuphonic/neutts-nano-german` | German | ~229M | German language |
| `neuphonic/neutts-nano-french` | French | ~229M | French language |
| `neuphonic/neutts-nano-spanish` | Spanish | ~229M | Spanish language |
| `neuphonic/neutts-*-q4-gguf` | varies | smaller | Quantized — faster, less memory |
| `neuphonic/neutts-*-q8-gguf` | varies | medium | Quantized — balanced |

Switch models using environment variables:

```bash
NEUTTS_BACKBONE="neuphonic/neutts-air" python mcp_server.py
```

---

## Configuration

All settings are optional — defaults work out of the box.

| Variable | Default | Description |
|----------|---------|-------------|
| `NEUTTS_BACKBONE` | `neuphonic/neutts-nano` | HuggingFace model repo |
| `NEUTTS_BACKBONE_DEVICE` | `cpu` | `cpu` or `cuda` for GPU |
| `NEUTTS_CODEC` | `neuphonic/neucodec` | Audio codec model |
| `NEUTTS_CODEC_DEVICE` | `cpu` | `cpu` or `cuda` for GPU |
| `NEUTTS_OUTPUT_DIR` | `./output` | Where WAV files are saved |
| `NEUTTS_SAMPLES_DIR` | `./samples` | Built-in speaker samples |
| `NEUTTS_SPEAKERS_DIR` | `./speakers` | Custom voice data |
| `NEUTTS_TRANSPORT` | `stdio` | `stdio`, `sse`, or `streamable-http` |
| `NEUTTS_HOST` | `127.0.0.1` | Bind address (SSE/HTTP only) |
| `NEUTTS_PORT` | `8000` | Bind port (SSE/HTTP only) |

### GPU Acceleration

For faster synthesis on NVIDIA GPUs:

```bash
NEUTTS_BACKBONE_DEVICE=cuda NEUTTS_CODEC_DEVICE=cuda python mcp_server.py
```

Requires PyTorch with CUDA support.

---

## Running as a Service

For production use, create a systemd service so it starts automatically:

```ini
# /etc/systemd/system/cheema-tts.service
[Unit]
Description=Cheema Text-to-Voice MCP Server
After=network.target

[Service]
Type=simple
WorkingDirectory=/path/to/CHeema-Text-to-Voice-MCP-Server
ExecStart=/path/to/venv/bin/python mcp_server.py --transport sse --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now cheema-tts
```

To expose it over HTTPS, put an Nginx or Caddy reverse proxy in front with these key settings for SSE:
- Disable proxy buffering (`proxy_buffering off`)
- Set a long read timeout (`proxy_read_timeout 86400`)
- Add `X-Accel-Buffering: no` header

---

## Troubleshooting

**Server won't start?**
- Check espeak-ng: `espeak-ng --version`
- Check dependencies: `pip list | grep -E "mcp|neutts|torch|soundfile"`

**No audio output?**
- Check the `output/` directory for WAV files
- Verify speaker name with `tts_list_speakers`

**Slow first run?**
- Normal — the first run downloads model weights from HuggingFace (~200-500MB). Cached after that.

**Want GPU acceleration?**
- Set `NEUTTS_BACKBONE_DEVICE=cuda` and `NEUTTS_CODEC_DEVICE=cuda`

---

## How It Works

1. The server loads the NeuTTS backbone model and audio codec on startup
2. Speaker voice prints (`.pt` files) are loaded into memory
3. When you request speech, text is phonemized and combined with the speaker's voice reference
4. The model generates speech tokens, decoded into a 24kHz waveform
5. Output is saved as a standard WAV file

---

## Project Structure

```
CHeema-Text-to-Voice-MCP-Server/
├── mcp_server.py       # MCP server entry point
├── neutts/             # NeuTTS engine
├── samples/            # Built-in speaker voices (.wav, .pt, .txt)
├── speakers/           # Custom cloned voices (auto-created)
├── output/             # Generated audio files (auto-created)
└── examples/           # Usage examples
```

---

## Credits

- **[NeuTTS](https://github.com/neuphonic/neutts)** by [Neuphonic](https://neuphonic.com/) — the TTS engine
- **[MCP Protocol](https://modelcontextprotocol.io)** by [Anthropic](https://anthropic.com/) — the AI tool standard

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

MIT License. The underlying NeuTTS models have their own licenses — see the [NeuTTS repository](https://github.com/neuphonic/neutts) for details.

---

<p align="center">
  <strong>Cheema Text-to-Voice MCP Server</strong><br>
  Give your AI assistant a voice.
</p>
