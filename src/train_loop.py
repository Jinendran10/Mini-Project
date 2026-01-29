from trainer import train_step
from weight_store import commit_weights
from jie_runner import run_jie       # to be provided by Person 1
from rlod_runner import run_rlod     # to be provided by Person 2

def train(dataloader, num_epochs):
    for epoch in range(1, num_epochs + 1):
        print(f"\nEpoch {epoch} start")

        # 1️⃣ Normal training
        for batch in dataloader:
            loss = train_step(batch)

        # 2️⃣ Occasionally run detection
        if epoch % 3 == 0:
            flagged = run_jie(epoch)
            run_rlod(flagged, epoch)

            # 3️⃣ SAFE point to apply new weights
            commit_weights()
            print("Weights committed")

        print(f"Epoch {epoch} end")
