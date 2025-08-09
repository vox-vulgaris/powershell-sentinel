# create_mini_dataset.py
import json
import random
import os

print("Loading full training set...")
# Correctly point to the location of the partitioned data
full_train_path = 'data/sets/training_set_v0.json'

with open(full_train_path, 'r') as f:
    full_train = json.load(f)
random.shuffle(full_train)

print("Creating subset...")
subset = full_train[:1000]
mini_train = subset[:900]
mini_val = subset[900:]

# Define the output directory
output_dir = 'scripts/prompt_engineering'
os.makedirs(output_dir, exist_ok=True) # Ensure the directory exists

train_path = os.path.join(output_dir, 'mini_train.json')
val_path = os.path.join(output_dir, 'mini_val.json')

print(f"Saving {len(mini_train)} samples to {train_path}")
with open(train_path, 'w') as f:
    json.dump(mini_train, f, indent=2)

print(f"Saving {len(mini_val)} samples to {val_path}")
with open(val_path, 'w') as f:
    json.dump(mini_val, f, indent=2)

print("\nDone. Mini-datasets created.")