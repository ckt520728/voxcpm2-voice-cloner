import faulthandler
faulthandler.enable()

import sys
print("Step 1: imports ok", file=sys.stderr, flush=True)

import torch
print(f"Step 2: torch {torch.__version__}", file=sys.stderr, flush=True)

# Import minicpm4 directly to avoid torchaudio import via voxcpm.__init__
import importlib.util, os
_base = r"Z:\.venv\Lib\site-packages\voxcpm"
for _mod, _path in [
    ("voxcpm.modules.minicpm4.config", os.path.join(_base, "modules", "minicpm4", "config.py")),
    ("voxcpm.modules.minicpm4.cache",  os.path.join(_base, "modules", "minicpm4", "cache.py")),
    ("voxcpm.modules.minicpm4.model",  os.path.join(_base, "modules", "minicpm4", "model.py")),
]:
    spec = importlib.util.spec_from_file_location(_mod, _path)
    mod  = importlib.util.module_from_spec(spec)
    sys.modules[_mod] = mod
    spec.loader.exec_module(mod)

from voxcpm.modules.minicpm4.config import MiniCPM4Config
from voxcpm.modules.minicpm4.model  import MiniCPMModel
print("Step 3: MiniCPMModel imported", file=sys.stderr, flush=True)

import json
with open(r"C:\Users\User\.cache\huggingface\hub\models--openbmb--VoxCPM2\snapshots\bffb3df5a29440629464e5e839f4d214c8714c3d\config.json") as f:
    cfg = json.load(f)

lm_cfg = MiniCPM4Config(**cfg["lm_config"])
print(f"Step 4: config loaded, hidden_size={lm_cfg.hidden_size}, layers={lm_cfg.num_hidden_layers}", file=sys.stderr, flush=True)

print("Step 5: creating MiniCPMModel...", file=sys.stderr, flush=True)
model = MiniCPMModel(lm_cfg)
print("Step 6: MiniCPMModel created ok", file=sys.stderr, flush=True)

print("Step 7: setup_cache...", file=sys.stderr, flush=True)
model.setup_cache(1, 8192, "cpu", torch.bfloat16)
print("Step 8: setup_cache ok", file=sys.stderr, flush=True)
