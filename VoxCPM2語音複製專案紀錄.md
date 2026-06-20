# VoxCPM2 語音複製專案完整紀錄

**日期：** 2026-06-20  
**專案：** https://github.com/ckt520728/voxcpm2-voice-cloner  
**目標：** 使用 VoxCPM2 複製聲音，生成附中文字幕的 MP4 影片

---

## 完成成果

| 產出物 | 路徑 |
|--------|------|
| 參考錄音 | `Z:\voices\朱國大的聲音\ref_voice.wav` |
| 合成語音 | `Z:\output\cloned_voice.wav`（171.8 秒，RTF≈5.9×） |
| 字幕檔 | `Z:\output\cloned_voice.srt`（46 段，Whisper medium） |
| 最終影片 | `Z:\output\cloned_voice.mp4`（1280×720，黑底白字字幕） |

---

## 系統環境

- Windows 11 Home
- NVIDIA RTX 3060（CUDA 12.8）
- Python 3.11.15（Astral CPython，uv 管理）
- PyTorch 2.7.0+cu128
- VoxCPM2 模型（openbmb/VoxCPM2，~4.7 GB，bfloat16）
- Whisper medium（openai-whisper）
- ffmpeg（影片合成）

---

## 踩坑紀錄與解法

### 坑 1：PowerShell 5.1 無法執行含中文字串的 install.ps1

**症狀：** 執行 `install.ps1` 時，PowerShell 5.1 對 Traditional Chinese 字串編碼報錯，腳本中止。  
**原因：** Windows PowerShell 5.1 預設 UTF-16 LE 編碼，讀取含中文的 `.ps1` 時發生解析錯誤。  
**解法：** 不執行 `install.ps1`，改為手動逐步執行安裝指令。

---

### 坑 2：專案路徑含中文字元導致各種工具失敗

**症狀：** 路徑 `G:\我的雲端硬碟\2026Agents\voxcpm2-voice-cloner` 在 PowerShell、Bash、Python 中均出現解析錯誤或亂碼。  
**原因：** Windows 工具對非 ASCII 路徑支援不一致。  
**解法：** 使用 `subst` 建立替代磁碟代號：
```bat
subst Z: "G:\我的雲端硬碟\2026Agents\voxcpm2-voice-cloner"
```
之後所有操作一律使用 `Z:\`，完全迴避中文路徑問題。  
**注意：** `subst` 在重開機後會消失，需要每次重新執行。

---

### 坑 3：PyTorch 2.11.0+cu128 在 Windows 上 Heap Corruption 導致崩潰

**症狀：** 執行 `clone.py` 或任何載入 VoxCPM2 模型的腳本時，隨機發生 exit code 139（Linux SIGSEGV）或 Windows access violation（0xC0000005），崩潰位置不固定：
- `StaticKVCache.__init__` 內的 `torch.zeros(...)` 
- `nn.Linear.__init__` 內的 `torch.empty(...)`

**原因：** PyTorch 2.11.0 在 Windows + Astral CPython 3.11.15 組合下存在 heap corruption bug，於模型初始化期間非確定性觸發。  
**嘗試但無效的修法：**
- 將 `cache.py` 中 `bfloat16` 改為 `float32`
- 將 `torch.zeros` 改為 `torch.empty`

**實際解法：** 降版 PyTorch：
```powershell
uv pip install "torch==2.7.0+cu128" --index-url https://download.pytorch.org/whl/cu128
```

**次要問題：** 降版後 torchaudio 仍為 2.11.0，載入時出現 `OSError: [WinError 127]`（DLL 找不到）。  
**解法：** 同步降版 torchaudio：
```powershell
uv pip install "torchaudio==2.7.0+cu128" --index-url https://download.pytorch.org/whl/cu128
```

**注意：** PyTorch 2.6.0+cu128 不存在，直接跳到 2.7.0。

---

### 坑 4：ffmpeg subtitles filter 無法處理含磁碟代號的路徑

**症狀：** ffmpeg `-vf subtitles='Z:\output\cloned_voice.srt'` 報錯：
```
Unable to parse "original_size" option value "/output/cloned_voice.srt" as image size
```
**原因：** ffmpeg 的 subtitles filter 用冒號 `:` 解析選項，`Z:` 中的冒號被當成選項分隔符，導致路徑被截斷。  
**解法：** 將 SRT 複製到無磁碟代號的路徑，或在 filter 字串中跳脫冒號：
```powershell
# 方法 A（最簡單）：複製到 C:\Users\... 暫存路徑
Copy-Item "Z:\output\cloned_voice.srt" "C:\Users\User\AppData\Local\Temp\sub.srt"

# 方法 B：在 filter 字串中跳脫磁碟代號冒號
-vf "subtitles='C\:/Users/User/AppData/Local/Temp/sub.srt':force_style='...'"
```

---

### 坑 5：Whisper 轉錄錯字（語音合成產生的語音）

Whisper medium 模型對 VoxCPM2 合成語音的轉錄出現以下錯誤，需手動修正：

| 錯誤 | 正確 | 所在段落 |
|------|------|----------|
| 進障科 | 腎臟科 | 第 5 段 |
| 醒斷 | 診斷 | 第 7 段 |

（其餘修正由使用者直接編輯 `.srt` 檔後重新渲染影片。）

---

## 完整執行流程

```
1. subst Z: "G:\我的雲端硬碟\2026Agents\voxcpm2-voice-cloner"
2. cd Z:\
3. uv pip install "torch==2.7.0+cu128" torchaudio==2.7.0+cu128 ...
4. 執行 launch_webui.bat → 瀏覽器開啟 http://127.0.0.1:7860 錄製參考聲音
5. Z:\.venv\Scripts\python.exe Z:\clone.py   # 生成 cloned_voice.wav（約 17 分鐘）
6. Z:\.venv\Scripts\python.exe -m whisper Z:\output\cloned_voice.wav \
       --model medium --language zh --output_format srt --output_dir Z:\output
7. 手動校對並修正 cloned_voice.srt
8. ffmpeg 合成最終 MP4（黑底 + 音訊 + 燒入字幕）
```

---

## 關鍵檔案說明

| 檔案 | 說明 |
|------|------|
| `Z:\clone.py` | 主要語音複製腳本 |
| `Z:\launch_webui.bat` | 啟動 Gradio 錄音介面（繞過中文路徑問題） |
| `Z:\texts\speech_script.txt` | 清理後的純文字語音稿（去除 Markdown 格式） |
| `Z:\.gpu_type` | 內容為 `cuda`，供 clone.py 選擇裝置用 |
| `Z:\voices\朱國大的聲音\ref_voice.wav` | 參考錄音（16kHz mono WAV） |
| `Z:\voices\朱國大的聲音\prompt.txt` | 參考錄音對應文字稿 |
