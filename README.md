# VoxCPM2 Voice Cloner

用 VoxCPM2 克隆你的聲音，生成任意語音。全自動安裝，自動偵測 GPU，**一個網頁搞定全部流程**。

## 特色

- **自動偵測 GPU**：NVIDIA CUDA / Intel Arc XPU / CPU 三種模式自動切換
- ** Ultimate Cloning**：同時使用參考音 + 逐字稿，連語氣節奏都一起複製
- **網頁操作**：`app.py` 提供完整網頁介面（錄音 → 克隆 → 生成 → 對話），瀏覽器開網址就能用
- **Apache-2.0 授權**：VoxCPM2 模型可商用

## 系統需求

- Windows 10/11（Linux/Mac 可自行調整 install 腳本）
- Python 3.10–3.12（安裝腳本會用 uv 自動建立 3.12 環境）
- 顯卡（擇一）：
  - NVIDIA GPU（CUDA 12+，約 8GB VRAM）
  - Intel Arc GPU（XPU，約 8GB VRAM，需自動 patch）
  - 無獨顯也可用 CPU（較慢，RTF 約 8x）
- 約 5GB 硬碟空間（模型權重）
- 麥克風

## 快速開始（三步）

### 1. 安裝

```powershell
git clone https://github.com/mathruffian-dot/voxcpm2-voice-cloner.git
cd voxcpm2-voice-cloner
.\install.ps1
```

安裝腳本自動完成：Python 3.12 venv / GPU 偵測 / PyTorch / voxcpm / XPU patch（若需要）

### 2. 啟動網頁工具

```powershell
.\.venv\Scripts\python.exe app.py
```

瀏覽器打開 `http://127.0.0.1:7860`，三個分頁：

| 分頁 | 功能 |
|------|------|
| 🎙️ 錄音 | 輸入聲音名稱 → 麥克風錄音（或上傳音檔）→ 存檔 |
| 🔊 生成 | 選聲音 → 輸入文字 → 生成克隆語音 → 播放/下載 |
| 💬 對話 | 選兩個聲音 → 寫對話腳本 → 生成多人對話 |

### 3. 使用流程

1. 切到「🎙️ 錄音」分頁 → 輸入聲音名稱 → 對著麥克風朗讀文字 → 存檔
2. 切到「🔊 生成」分頁 → 選擇聲音 → 輸入文字 → 按生成 → 播放

> 💡 如果瀏覽器找不到麥克風，可以先用 `record.py` 命令列錄音，再用網頁「上傳音檔」。
5. 若為 Intel Arc，自動套用 XPU patch

### 2. 錄製參考音

有兩種方式：

**方式 A：網頁介面（推薦）**

```powershell
.\.venv\Scripts\python.exe webui_record.py
```

瀏覽器自動開啟，有錄音按鈕、逐字稿顯示，錄完自動存檔。

**方式 B：命令列**

```powershell
.\.venv\Scripts\python.exe record.py --voice 我的聲音
```

螢幕會顯示一段文字，對著麥克風自然地朗讀，念完按 Enter 停止。

### 3. 生成克隆語音

```powershell
.\.venv\Scripts\python.exe clone.py "你好，這是我的克隆聲音。" --voice 我的聲音
```

或從文字檔生成：

```powershell
.\.venv\Scripts\python.exe clone.py --file my_script.txt
```

輸出檔案預設在 `output/cloned_voice.wav`。

## 目錄結構

```
voxcpm2-voice-cloner/
├── app.py                    # 主程式：網頁工具（錄音 + 克隆 + 對話）
├── install.ps1               # 自動安裝腳本（偵測 GPU + 建環境）
├── webui_record.py           # 獨立錄音介面（Gradio，替代方案）
├── record.py                 # 命令列錄音（替代方案）
├── clone.py                  # 命令列語音生成（替代方案）
├── dialogue.py               # 命令列對話生成（替代方案）
├── texts/
│   └── sample_text.txt       # 給使用者朗讀的範例文字
├── voices/                   # 聲音資料夾（.gitignore 排除，本地保留）
│   └── <你的聲音>/           # 用 app.py 錄音時自動建立
│       ├── ref_voice.wav     # 參考音
│       └── prompt.txt        # 逐字稿
├── patches/
│   ├── utils.py              # XPU device 支援 patch（Intel Arc 用）
│   └── repatch_xpu.ps1       # voxcpm 更新後自動重 patch
├── output/                   # 生成的語音輸出於此
└── .gpu_type                 # 安裝時記錄的 GPU 類型（.gitignore 排除）
```

## 命令列工具（替代方案，不需 GUI 時可用）

## GPU 支援對照

| GPU | 模式 | PyTorch | 需要 patch | 效能（參考） |
|-----|------|---------|-----------|-------------|
| NVIDIA (CUDA 12+) | cuda | cu128 wheel | 不需要 | RTF ~0.3（RTX 4090） |
| Intel Arc (XPU) | xpu | xpu wheel | 需要（自動） | RTF ~2.0（Arc 140T） |
| 無獨顯 | cpu | cpu wheel | 不需要 | RTF ~8.0 |

> RTF = 生成 N 秒語音所需的時間倍率，越低越快。

## Intel Arc (XPU) 注意事項

VoxCPM2 官方目前只支援 NVIDIA CUDA。Intel Arc 的 XPU 支援透過 patch 實現：

- `install.ps1` 會自動套用 patch
- 若 `pip install -U voxcpm` 更新了套件，patch 會被覆蓋
- 執行 `patches\repatch_xpu.ps1` 即可恢復：

```powershell
.\patches\repatch_xpu.ps1
```

### 根治計畫

本專案已向 [OpenBMB/VoxCPM](https://github.com/OpenBMB/VoxCPM) 提交 XPU 支援 PR（對應 [Issue #215](https://github.com/OpenBMB/VoxCPM/issues/215)）。官方合併後，patch 機制將自動退役，`pip install voxcpm` 即原生支援 Intel Arc。

## 授權

- VoxCPM2 模型與程式碼：[Apache-2.0](https://github.com/OpenBMB/VoxCPM/blob/main/LICENSE)（可商用）
- 本專案腳本：MIT
