from .model_loader import model, tokenizer
import yaml

with open("config.yaml", "r") as f:
    cfg = yaml.safe_load(f)

_max_length = (
    cfg.get("jie", {}).get("max_length")
    or cfg.get("training", {}).get("max_seq_length")
    or 512
)


def compute_gradients_and_hidden(texts):
    inputs = tokenizer(
        texts,
        return_tensors="pt",
        truncation=True,
        max_length=_max_length,
        padding=True
    )

    outputs = model(**inputs)
    loss = outputs.logits.mean()
    loss.backward()

    last_hidden = outputs.hidden_states[-1].detach()

    gradients = {
        name: p.grad.detach()
        for name, p in model.named_parameters()
        if p.grad is not None
    }

    model.zero_grad()  # IMPORTANT
    return last_hidden, gradients
