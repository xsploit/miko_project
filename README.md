# 🦊 Miko AI VTuber

An AI VTuber that chats via a local LLM, speaks through an external TTS server, and animates a VRM avatar in real time via WebSocket.

<div align="center">

[![Windows](https://img.shields.io/badge/Windows-10/11-blue?style=for-the-badge&logo=windows)](https://www.microsoft.com/windows)
[![Python](https://img.shields.io/badge/Python-3.10+-yellow?style=for-the-badge&logo=python)](https://www.python.org/)
[![Ollama](https://img.shields.io/badge/LLM-Ollama-00B2FF?style=for-the-badge)](https://ollama.com)
[![WebSocket](https://img.shields.io/badge/WebSocket-Realtime-00C853?style=for-the-badge&logo=socket.io)](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

</div>

---

## 🌟 What Miko Does
- 🧠 Local LLM chat (Ollama by default)
- 🔊 Low-latency, chunked TTS playback (external server, e.g., GPT-SoVITS)
- 🎭 VRM animation signals (`tts_start`, `tts_end`) over WebSocket
- 🎤 Optional push-to-talk voice input (faster-whisper)
- ⚙️ YAML-driven configuration (providers, audio, TTS, personality)

---

## 🚀 Quick Start
1) Create and activate a virtual environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
2) Install dependencies
```powershell
pip install -r requirements.txt
```
3) Start your TTS server (separate project)
- Must expose `/tts` on `http://127.0.0.1:9880`
- For streaming WAV, return WAV header, then raw PCM chunks
- Prefer an absolute `ref_audio_path` on Windows
4) Run Miko
```powershell
python miko.py
```
5) (Optional) Use the Setup UI
```powershell
python setup.py
```
- Save audio/TTS/personality settings, then click Start to launch VRM loader and Miko.

---

## 📦 All-in-One (Viewer + Miko)
This repo includes a VRM viewer/loader (in `vrmloader/`) and Miko in one place.

- Use the Setup UI to launch both processes with your saved config:
  - It starts `vrmloader/vrmloader.exe` (VRM viewer) first
  - Then launches `miko.py` which connects and emits `tts_start/tts_end`
  - WebSocket: `ws://localhost:{vrm_websocket_port}` (default `8765`)

- Manual launch (alternative):
  1) Start the viewer: `./vrmloader/vrmloader.exe`
  2) In another terminal, run: `python miko.py`
  3) Ensure the viewer is connected and listening for VRM WebSocket messages

Note: The TTS server (e.g., GPT-SoVITS) is external and must be started separately.

---

## 🗂️ Project Layout (key files)
- `miko.py` — main app (LLM chat + TTS streaming + VRM signals)
- `setup.py` — PyQt6 Setup UI (devices, ASR, personality, launch)
- `miko_config.yaml` — main configuration (providers, audio, TTS, ASR, personality)
- `audio_config.json` — persisted output device
- `modules/asr.py` — ASR manager (used by `miko.py`)
- `modules/audio.py` — audio playback thread
- `vrmloader/` — example VRM resources and `vrmloader.exe` viewer

> Note: `miko.py` currently inlines most logic and only imports `ASRManager` from `modules.asr`. The Setup UI reads audio utilities from `modules/audio_utils` and stores `modules/miko_personality.json` for compatibility.

---

## ⚙️ Configuration (miko_config.yaml)
Miko reads from YAML and falls back gracefully.

- 🧠 Providers & Model
  - `provider`: active provider key (e.g., `ollama`)
  - `providers.{provider}.model`: model name used by `ollama.chat`
  - Fallback: `ollama_config.selected_model`

- 🔊 TTS
  - `tts_config.server_url`: e.g., `http://127.0.0.1:9880` (fallback to top-level `tts_server_url`)
  - `tts_config.text_lang`, `prompt_lang`, `ref_audio_path`, `prompt_text`, `media_type`
  - `tts_config.streaming_mode`, `parallel_infer` (GET flow forces `streaming_mode=true` for compatibility)
  - Missing fields inherit from `sovits_config` when present

- 🔈 Audio Devices
  - `audio_devices.device_index`: output device (or `null` for system default)
  - `audio_devices.asr_enabled`, `asr_model`, `asr_device`, `push_to_talk_key`, `input_device_id`

- 🎤 ASR Fallback (if not using `audio_devices`)
  - `asr_config.enabled`, `model`, `device`, `push_to_talk_key`, `input_device_id`

- 🎭 VRM
  - `vrm_websocket_port` (default `8765`)

- 🎭 Personality
  - `personality.name`, `system_prompt`, `greeting`, `farewell`
  - Current build forces a fixed welcome TTS string for stability during testing

---

## 🕹️ Setup UI (Optional)
Run the GUI to configure and launch.
```powershell
python setup.py
```
- Select input/output devices, ASR, and voice settings
- Save updates to `miko_config.yaml` and `audio_config.json`
- Launch flow: starts `vrmloader/vrmloader.exe`, then runs `miko.py`

---

## 🎭 VRM Integration
- WebSocket server: `ws://localhost:{vrm_websocket_port}` (default `8765`)
- Messages sent to all connected VRM clients:
  - `{ "type": "tts_start", "text": "..." }`
  - `{ "type": "tts_end" }`
- Use `vrmloader/vrmloader.exe` or your own VRM viewer that consumes these events to trigger lip-sync/animations.

---

## 🔌 TTS API Compatibility
Miko’s TTS client performs a GET request to `/tts` with parameters like:
```
text, text_lang, ref_audio_path, prompt_text, prompt_lang,
streaming_mode=true, parallel_infer, media_type=wav,
batch_size, top_k, top_p, temperature, text_split_method,
speed_factor, fragment_interval, repetition_penalty, seed
```
Notes:
- For streaming WAV, the server should return the WAV header first, then raw PCM chunks
- If you get HTTP 400, verify required params and make `ref_audio_path` absolute

---

## 🧱 External GPT-SoVITS API Server (CUDA/FP16)
You must run a TTS server separately. For best latency/quality, use a CUDA-enabled GPT-SoVITS build and run its API server.

### Requirements
- NVIDIA GPU + recent drivers
- CUDA-enabled PyTorch in the GPT-SoVITS environment (CUDA 12.x commonly used)
- FastAPI + Uvicorn in that environment

### Typical setup (in your GPT-SoVITS folder)
```powershell
# 1) Create and activate a dedicated env (example with conda)
conda create -n gpt-sovits python=3.10 -y
conda activate gpt-sovits

# 2) Install CUDA-enabled PyTorch (adjust CUDA version as needed)
# Example for CUDA 12.1:
pip install --index-url https://download.pytorch.org/whl/cu121 torch torchvision torchaudio

# 3) Install project requirements (from GPT-SoVITS repo)
pip install -r requirements.txt

# 4) API server deps
pip install fastapi uvicorn soundfile websockets

# 5) Launch the API server (adjust paths)
python api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml
```

### FP16/CUDA guidance
- Use CUDA builds of PyTorch; verify with `python -c "import torch; print(torch.cuda.is_available())"`
- Prefer FP16 where supported (model/config dependent)
- Keep `streaming_mode=true` for GET streaming (Miko enforces this automatically)

### Using a modified API server (with VRM signals)
- If you maintain a modified API (e.g., similar to `vrmloader/api_v3.py`) that emits `tts_start`/`tts_end`, run it inside the GPT-SoVITS environment (not this repo’s venv), so all model deps and CUDA builds are available
- Keep it on `127.0.0.1:9880` to match Miko’s default configuration

---

### Using the prebuilt v2pro package (go-webui.bat)
If you downloaded a precompiled GPT-SoVITS v2pro package, edit its `go-webui.bat` to launch the API server on the expected host/port:

Example file: `go-webui.bat`
```bat
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
cd /d "%SCRIPT_DIR%"
set "PATH=%SCRIPT_DIR%\runtime;%PATH%"
runtime\python.exe -I api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS\configs\tts_infer.yaml
pause
```
Notes:
- Ensure the `-c` path points to your actual `tts_infer.yaml`
- Keep the port `9880` (or change `miko_config.yaml` → `tts_config.server_url` accordingly)

---

## 🎤 Voice Input (ASR)
- Hold the configured hotkey (default `shift`) to record; release to transcribe
- Requires `faster-whisper` and a working mic; enable in YAML (`asr_enabled: true`)

---

## 🧪 Running From Source
```powershell
.\.venv\Scripts\Activate.ps1
python miko.py
```
- Ensure TTS server is running at configured URL
- If using Ollama, ensure `ollama serve` is running and the model is available

---

## 📦 Building a Windows EXE (Optional)
Runtime installs are skipped when frozen. Example onedir build:
```powershell
pyinstaller --noconfirm --clean --onedir --name MikoVTuber ^
  --add-data "miko_config.yaml;." ^
  --add-data "audio_config.json;." ^
  --add-data "main_sample.wav;." ^
  --add-data "modules\miko_personality.json;modules" ^
  --add-data "vrmloader\vrmloader.exe;vrmloader" ^
  --hidden-import aiohttp --hidden-import websockets ^
  --hidden-import sounddevice --hidden-import numpy --hidden-import requests ^
  --paths modules miko.py
```
Run from `dist\MikoVTuber` so relative assets are found.

---

## 🛠️ Troubleshooting
- ❌ TTS returns 400
  - Check that required params are present
  - Use an absolute `ref_audio_path`
  - Keep `streaming_mode=true` for GET-based streaming
- ⚠️ Event loop warnings
  - VRM signal scheduling is guarded; run from a console to capture logs
- 🔇 No audio output
  - Pick a different output device in the menu
  - Verify Windows sound settings and sample rate
- 🎙️ ASR not working
  - Confirm `asr_enabled`, mic permissions, and `input_device_id`
- 🧊 EXE instantly closes
  - Run from a console to capture output; ensure the external TTS server is started separately

---

## 🧩 Architecture (High Level)
- `miko.py`
  - YAML config → LLM chat via Ollama → sentence buffering → TTS GET `/tts`
  - Audio chunks → playback thread → `tts_start` / `tts_end` → VRM WebSocket clients
  - Optional ASR via `ASRManager` (push-to-talk)
- `setup.py`
  - PyQt6 GUI to configure YAML, select devices, and launch VRM loader then Miko

---

Built for creators who want reliable, low-latency AI VTubing with deterministic animation sync. Have fun with Miko! ✨

---

## 🙌 Credits & Inspiration
- Inspired by the public Riko Project by Just Rayen. In canon, Miko is the “shameless clone with blue streaks” (Riko has red) who totally “stole” Riko’s code and attitude — purely a joke and tribute. See: [rayenfeng/riko_project](https://github.com/rayenfeng/riko_project)
- TTS powered externally by GPT-SoVITS variants. For the latest builds and notes, see: [RVC-Boss/GPT-SoVITS Releases](https://github.com/RVC-Boss/GPT-SoVITS/releases)

---

## 🔬 Differences vs upstream GPT-SoVITS api_v2.py
Reference: [RVC-Boss/GPT-SoVITS api_v2.py](https://github.com/RVC-Boss/GPT-SoVITS/blob/main/api_v2.py)

- CUDA/TF32 optimizations
  - Enables cuDNN benchmark and TF32 fast paths; attempts `torch.set_float32_matmul_precision("high")`
  - Tries enabling CUDA SDP kernels (FlashAttention/mem-efficient)
  - Sets `BIGVGAN_USE_CUDA_KERNEL=1` and attempts fused-kernel toggles on BigVGAN
- Performance logging
  - Timer and GPU memory helpers around pipeline init and generation
  - Suppresses noisy http logs (urllib3/httpx)
- Memory hygiene
  - Calls `torch.cuda.empty_cache()` after generation to reduce fragmentation
- Audio packing / formats
  - Unified `pack_audio` for wav/raw/ogg/aac (ogg via soundfile, aac via ffmpeg pipe)
  - For streaming WAV, sends a one-time WAV header, then raw PCM chunks
- Request validation
  - Enforces required fields and validates languages against `tts_config.languages`
  - Rejects `ogg` when not in streaming mode
- Endpoints
  - GET/POST `/tts` compatible with upstream, with enhanced streaming behavior
  - `/control` (restart/exit), `/set_gpt_weights`, `/set_sovits_weights`, `/set_refer_audio`
  - New diagnostics: `/cuda_info` and `/health`
- Runtime/boot
  - CLI args: `-a` (bind), `-p` (port), `-c` (config) with explicit boot logs
  - Forces `workers=1` for uvicorn

In short: keeps upstream contract, adds GPU fast-paths (TF32/SDP/BigVGAN), stricter validation, richer formats, explicit WAV streaming headering, memory cleanup, and health/CUDA introspection for low-latency, long-running GPU use.
