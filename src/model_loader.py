import yaml
from transformers import AutoTokenizer, AutoModelForCausalLM

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

if "model" not in config:
    raise RuntimeError("Missing 'model' section in config.yaml")

if "name" not in config["model"] or "tokenizer" not in config["model"]:
    raise RuntimeError("Model name/tokenizer missing in config.yaml")

model_name = config["model"]["name"]
tokenizer_name = config["model"]["tokenizer"]

tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)

tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    output_hidden_states=True
)

model.eval()
