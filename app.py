#!/usr/bin/env python3
"""
app.py - VoxCPM2 Voice Cloner 完整網頁工具
一個網址搞定：錄音 → 克隆 → 對話

用法：
  python app.py              # http://127.0.0.1:7860
  python app.py --port 8080  # 指定 port
"""

import os
import sys
import time
import json
import wave
import base64
import threading
import argparse
import numpy as np
import gradio as gr

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_RATE = 16000

# ============================================================
#  Helper: model lazy-loading
# ============================================================
_model = None
_model_lock = threading.Lock()
_device_info = None


def detect_device():
    """Auto-detect GPU type or read from .gpu_type file."""
    gpu_type_file = os.path.join(REPO_DIR, ".gpu_type")
    if os.path.exists(gpu_type_file):
        with open(gpu_type_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    import torch
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch, "xpu") and torch.xpu.is_available():
        return "xpu"
    return "cpu"


def load_model():
    """Lazy-load VoxCPM2 model (thread-safe, single instance)."""
    global _model, _device_info
    if _model is not None:
        return _model, _device_info

    with _model_lock:
        if _model is not None:
            return _model, _device_info

        from voxcpm import VoxCPM
        dev = detect_device()
        _model = VoxCPM.from_pretrained(
            "openbmb/VoxCPM2", load_denoiser=False, device=dev, optimize=False
        )
        _device_info = f"{dev}  |  bfloat16  |  Arc 140T 16GB" if dev == "xpu" else dev
        return _model, _device_info


# ============================================================
#  Voice management
# ============================================================
def list_voices():
    """Scan voices/ dir and return list of voice names."""
    vdir = os.path.join(REPO_DIR, "voices")
    if not os.path.exists(vdir):
        return []
    voices = []
    for name in sorted(os.listdir(vdir)):
        full = os.path.join(vdir, name)
        if os.path.isdir(full) and os.path.exists(os.path.join(full, "ref_voice.wav")):
            voices.append(name)
    return voices


def get_voice_files(name):
    """Return (ref_wav_path, prompt_text) for a voice name."""
    vdir = os.path.join(REPO_DIR, "voices", name)
    wav = os.path.join(vdir, "ref_voice.wav")
    prompt = os.path.join(vdir, "prompt.txt")
    txt = ""
    if os.path.exists(prompt):
        with open(prompt, "r", encoding="utf-8") as f:
            txt = f.read().strip()
    return wav, txt


def save_recording(audio_data, voice_name):
    """
    audio_data: Gradio Audio component output (sampling_rate, numpy_array)
    voice_name: str
    Returns: status message
    """
    if audio_data is None:
        return "❌ 尚未錄音或上傳音檔。"

    if not voice_name or not voice_name.strip():
        return "❌ 請輸入聲音名稱。"

    name = voice_name.strip()
    sr, audio = audio_data

    # Convert to mono
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    # Resample to 16kHz if needed
    if sr != SAMPLE_RATE:
        import resampy
        audio = resampy.resample(audio, sr, SAMPLE_RATE)

    # Normalize
    peak = np.abs(audio).max()
    if peak > 0:
        audio = audio / peak * 0.95

    # Save wav
    vdir = os.path.join(REPO_DIR, "voices", name)
    os.makedirs(vdir, exist_ok=True)
    import soundfile as sf
    wav_path = os.path.join(vdir, "ref_voice.wav")
    sf.write(wav_path, audio.astype(np.float32), SAMPLE_RATE)

    # Save prompt text (from the default sample text)
    prompt_path = os.path.join(vdir, "prompt.txt")
    sample_text = load_sample_text()
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(sample_text)

    duration = len(audio) / SAMPLE_RATE
    return (
        f"✅ 錄音已儲存！\n\n"
        f"  聲音: {name}\n  時長: {duration:.1f}s\n  取樣率: {SAMPLE_RATE}Hz"
    )


def load_sample_text():
    path = os.path.join(REPO_DIR, "texts", "sample_text.txt")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


# ============================================================
#  Tab 1: 錄音
# ============================================================
def refresh_voices():
    voices = list_voices()
    return gr.Dropdown(choices=voices, value=voices[0] if voices else None)


def on_save_record(audio_data, voice_name):
    return save_recording(audio_data, voice_name)


# ============================================================
#  Tab 2: 生成 / 克隆
# ============================================================
def on_generate(voice_name, gen_text, progress=gr.Progress()):
    if not voice_name:
        return None, "❌ 請先選擇聲音（請切到「錄音」分頁錄製或上傳音檔）。"

    if not gen_text or not gen_text.strip():
        return None, "❌ 請輸入要生成的文字。"

    progress(0.05, desc="載入模型中...")
    model, dev_info = load_model()

    ref_wav, prompt_text = get_voice_files(voice_name)
    if not os.path.exists(ref_wav):
        return None, f"❌ 找不到聲音檔: {ref_wav}"

    progress(0.3, desc="生成語音中...")
    t0 = time.time()
    wav = model.generate(
        text=gen_text.strip(),
        prompt_wav_path=ref_wav,
        prompt_text=prompt_text,
        reference_wav_path=ref_wav,
        cfg_value=1.5,
        inference_timesteps=10,
    )
    elapsed = time.time() - t0
    duration = len(wav) / model.tts_model.sample_rate

    import soundfile as sf
    out_path = os.path.join(REPO_DIR, "output", f"{voice_name}_{int(time.time())}.wav")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    sf.write(out_path, wav, model.tts_model.sample_rate)

    info = (
        f"✅ 生成完成！\n\n"
        f"  聲音: {voice_name}\n"
        f"  裝置: {dev_info}\n"
        f"  語音長度: {duration:.1f}s\n"
        f"  生成耗時: {elapsed:.1f}s  (RTF={elapsed/duration:.1f})\n"
        f"  檔案: {out_path}"
    )
    return (model.tts_model.sample_rate, wav), info


# ============================================================
#  Tab 3: 對話
# ============================================================
DEFAULT_DIALOGUE = (
    "三帥媽：你今天怎麼這麼晚才回來？\n"
    "三師爸：喔，剛剛在弄 AI 語音的東西，搞到忘記時間了。\n"
    "三帥媽：AI 語音？就是那個可以模仿別人聲音的嗎？\n"
    "三師爸：對啊，開源的，還可以商用，很厲害吧。\n"
    "三帥媽：那它有辦法模仿我的聲音嗎？\n"
    "三師爸：你現在聽到的就是你的聲音啊，我們正在對話呢。\n"
    "三帥媽：哇，真的假的！那我以後不用自己錄音了？\n"
    "三師爸：哈，理論上是啦，但真人還是有溫度啦。"
)


def parse_dialogue(script):
    """Parse dialogue script into list of (speaker, text)."""
    lines = []
    for line in script.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        if "：" in line:
            speaker, text = line.split("：", 1)
        elif ":" in line:
            speaker, text = line.split(":", 1)
        else:
            continue
        lines.append((speaker.strip(), text.strip()))
    return lines


def on_dialogue(script, progress=gr.Progress()):
    lines = parse_dialogue(script)
    if len(lines) < 2:
        return None, "❌ 對話格式錯誤。請用「說話者：文字」格式，每行一句。"

    progress(0.05, desc="載入模型中...")
    model, dev_info = load_model()

    # Preload all needed voices
    speakers = set(s for s, _ in lines)
    voice_data = {}
    for spk in speakers:
        ref_wav, prompt_text = get_voice_files(spk)
        if not os.path.exists(ref_wav):
            return None, f"❌ 找不到聲音 '{spk}' 的參考音檔。請先錄製。"
        voice_data[spk] = (ref_wav, prompt_text)

    clips = []
    total = len(lines)
    for i, (speaker, text) in enumerate(lines):
        progress(0.1 + 0.85 * (i / total), desc=f"生成 {speaker}: {text[:20]}...")
        ref_wav, prompt_text = voice_data[speaker]
        wav = model.generate(
            text=text,
            prompt_wav_path=ref_wav,
            prompt_text=prompt_text,
            reference_wav_path=ref_wav,
            cfg_value=1.5,
            inference_timesteps=10,
        )
        pause = np.zeros(int(0.35 * model.tts_model.sample_rate), dtype=wav.dtype)
        clips.append(wav)
        clips.append(pause)

    full_audio = np.concatenate(clips)
    duration = len(full_audio) / model.tts_model.sample_rate

    import soundfile as sf
    out_path = os.path.join(REPO_DIR, "output", f"dialogue_{int(time.time())}.wav")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    sf.write(out_path, full_audio, model.tts_model.sample_rate)

    info = (
        f"✅ 對話生成完成！\n\n"
        f"  {len(lines)} 句對話\n"
        f"  總長度: {duration:.1f}s\n"
        f"  檔案: {out_path}"
    )
    return (model.tts_model.sample_rate, full_audio), info


# ============================================================
#  UI Builder
# ============================================================
def build_ui():
    sample_text = load_sample_text()
    current_voices = list_voices()

    with gr.Blocks(title="VoxCPM2 Voice Cloner") as app:
        gr.Markdown(
            "# 🎙️ VoxCPM2 Voice Cloner\n"
            "錄音 → 克隆聲音 → 生成語音 → 多人對話，全部在瀏覽器完成。"
        )

        with gr.Tabs():
            # ==================== TAB 1: 錄音 ====================
            with gr.Tab("🎙️ 錄音"):
                gr.Markdown("### 錄製你的參考音\n對著麥克風朗讀下方文字，錄完按停止。")

                with gr.Row():
                    voice_name_input = gr.Textbox(
                        label="聲音名稱",
                        placeholder="例如：三師爸、三帥媽",
                        scale=2,
                    )
                    text_to_read = gr.Textbox(
                        label="要朗讀的文字（可自行修改）",
                        value=sample_text,
                        lines=4,
                        scale=3,
                    )

                audio_input = gr.Audio(
                    label="麥克風錄音 或 上傳音檔",
                    type="numpy",
                    sources=["microphone", "upload"],
                )

                with gr.Row():
                    save_btn = gr.Button("💾 存檔", variant="primary", size="lg")
                    refresh_btn = gr.Button("🔄 重新整理聲音列表", size="lg")

                save_msg = gr.Textbox(label="狀態", lines=4, interactive=False)

                save_btn.click(
                    fn=on_save_record,
                    inputs=[audio_input, voice_name_input],
                    outputs=[save_msg],
                )

            # ==================== TAB 2: 生成 ====================
            with gr.Tab("🔊 生成"):
                gr.Markdown("### 用克隆的聲音生成語音")

                with gr.Row():
                    voice_select = gr.Dropdown(
                        label="選擇聲音",
                        choices=current_voices,
                        value=current_voices[0] if current_voices else None,
                        scale=1,
                    )
                    refresh_btn.click(
                        fn=refresh_voices,
                        outputs=[voice_select],
                    )

                gen_text_input = gr.Textbox(
                    label="要生成的文字",
                    placeholder="輸入任意文字，AI 會用你選擇的聲音念出來...",
                    lines=4,
                )

                with gr.Row():
                    gen_btn = gr.Button("🚀 生成語音", variant="primary", size="lg")

                gen_audio_output = gr.Audio(label="生成的語音", interactive=False)
                gen_info = gr.Textbox(label="資訊", lines=5, interactive=False)

                gen_btn.click(
                    fn=on_generate,
                    inputs=[voice_select, gen_text_input],
                    outputs=[gen_audio_output, gen_info],
                )

            # ==================== TAB 3: 對話 ====================
            with gr.Tab("💬 對話"):
                gr.Markdown(
                    "### 多人對話生成\n"
                    "每行格式：`說話者：文字`。支援兩個以上聲音交叉對話。"
                )

                dialogue_input = gr.Textbox(
                    label="對話腳本",
                    value=DEFAULT_DIALOGUE,
                    lines=10,
                )

                dialogue_btn = gr.Button("🚀 生成對話", variant="primary", size="lg")
                dialogue_audio = gr.Audio(label="生成的對話", interactive=False)
                dialogue_info = gr.Textbox(label="資訊", lines=4, interactive=False)

                dialogue_btn.click(
                    fn=on_dialogue,
                    inputs=[dialogue_input],
                    outputs=[dialogue_audio, dialogue_info],
                )

    return app


def main():
    parser = argparse.ArgumentParser(description="VoxCPM2 Voice Cloner 網頁工具")
    parser.add_argument("--port", "-p", type=int, default=7860, help="Port (default: 7860)")
    parser.add_argument("--share", action="store_true", help="Create public Gradio link")
    args = parser.parse_args()

    app = build_ui()
    app.launch(server_port=args.port, share=args.share, theme=gr.themes.Soft())


if __name__ == "__main__":
    main()
