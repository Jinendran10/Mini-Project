import yaml
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# ---- FIXED CONFIG HANDLING ----

if "model" not in config:
    raise RuntimeError("Missing 'model' section in config.yaml")

# Use dev_model if available, else fallback to target_model
model_name = config["model"].get("dev_model") or config["model"].get("target_model")

if model_name is None:
    raise RuntimeError("No model specified in config.yaml (dev_model or target_model missing)")

# Load tokenizer and model
tokenizer = AutoTokenizer.from_pretrained(model_name)

# Fix for GPT models (no pad token)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    output_hidden_states=True
)

requested_device = config["model"].get("device", "cpu")

if requested_device == "cuda" and torch.cuda.is_available():
    device = torch.device("cuda")
else:
    device = torch.device("cpu")

model.to(device)

model.eval()
