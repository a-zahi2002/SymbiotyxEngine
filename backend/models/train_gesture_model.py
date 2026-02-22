import os
import sys
import json
import glob
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
from gesture_classifier import GestureClassifier, save_model

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DATA_RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
DATA_PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
DATA_AUGMENT_DIR = os.path.join(PROJECT_ROOT, "data", "augment")

os.makedirs(DATA_PROCESSED_DIR, exist_ok=True)
os.makedirs(DATA_AUGMENT_DIR, exist_ok=True)

TARGET_FRAMES = 50
FEATURE_DIM = 63  # 21 landmarks * 3 (x,y,z)

def process_sequence(frames):
    """
    Interpolates a sequence of frames to a fixed TARGET_FRAMES length.
    Returns: numpy array of shape (TARGET_FRAMES, FEATURE_DIM)
    """
    if not frames:
        return np.zeros((TARGET_FRAMES, FEATURE_DIM))
    
    # Extract features per frame
    sequence_features = []
    for f in frames:
        landmarks = f.get("landmarks", [])
        frame_features = []
        
        # If touch gesture, it may only have 1 landmark.
        # We process whatever landmarks exist and pad the rest to 21 landmarks (63 features)
        for lm in landmarks:
            frame_features.extend([lm.get("x", 0.0), lm.get("y", 0.0), lm.get("z", 0.0)])
            
        while len(frame_features) < FEATURE_DIM:
            frame_features.append(0.0)
            
        sequence_features.append(frame_features[:FEATURE_DIM])
        
    sequence_features = np.array(sequence_features)
    
    # Interpolation
    num_frames = sequence_features.shape[0]
    if num_frames == TARGET_FRAMES:
        return sequence_features
        
    indices = np.linspace(0, num_frames - 1, TARGET_FRAMES)
    interpolated = np.zeros((TARGET_FRAMES, FEATURE_DIM))
    for i in range(FEATURE_DIM):
        interpolated[:, i] = np.interp(indices, np.arange(num_frames), sequence_features[:, i])
        
    return interpolated

def augment_sequence(sequence):
    """
    Adds low levels of Gaussian noise to simulate jitter/variability.
    """
    noise = np.random.normal(0, 0.01, sequence.shape)
    return sequence + noise

def load_dataset():
    """
    Loads JSON files, processes/augments, and builds the dataset
    """
    print("[INFO] Loading and processing dataset...")
    X, y = [], []
    class_names = []
    
    # Let's inspect data/raw
    for user_folder in os.listdir(DATA_RAW_DIR):
        user_path = os.path.join(DATA_RAW_DIR, user_folder)
        if not os.path.isdir(user_path): continue
            
        for gesture_folder in os.listdir(user_path):
            gesture_path = os.path.join(user_path, gesture_folder)
            if not os.path.isdir(gesture_path): continue
                
            if gesture_folder not in class_names:
                class_names.append(gesture_folder)
            
            class_id = class_names.index(gesture_folder)
            
            # Read files
            for file_path in glob.glob(os.path.join(gesture_path, "*.json")):
                with open(file_path, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        continue
                        
                frames = data.get("frames", [])
                if not frames: continue
                    
                processed_seq = process_sequence(frames)
                X.append(processed_seq)
                y.append(class_id)
                
                # Optionally augment
                X.append(augment_sequence(processed_seq))
                y.append(class_id)

    if not X:
        print("[WARN] No valid data found in raw directories.")
        return None, None, {}

    X = np.array(X, dtype=np.float32)
    y = np.array(y, dtype=np.int64)
    class_map = {i: name for i, name in enumerate(class_names)}
    print(f"[INFO] Dataset loaded: {X.shape[0]} sequences, {len(class_names)} classes.")
    
    return torch.tensor(X), torch.tensor(y), class_map

def main():
    X_tensor, y_tensor, class_map = load_dataset()
    if X_tensor is None:
        return
        
    dataset = TensorDataset(X_tensor, y_tensor)
    dataloader = DataLoader(dataset, batch_size=16, shuffle=True)
    
    num_classes = len(class_map)
    model = GestureClassifier(input_dim=FEATURE_DIM, num_classes=num_classes)
    
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    epochs = 50
    print(f"[INFO] Started Training on classes: {class_map}")
    model.train()
    for epoch in range(epochs):
        epoch_loss = 0
        correct = 0
        total = 0
        
        for batch_X, batch_y in dataloader:
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            
            epoch_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            total += batch_y.size(0)
            correct += (predicted == batch_y).sum().item()
            
        if (epoch + 1) % 10 == 0:
            print(f"Epoch {epoch+1}/{epochs} | Loss: {epoch_loss/len(dataloader):.4f} | Acc: {100.*correct/total:.2f}%")
            
    print("[INFO] Training complete.")
    save_model(model, class_map)

if __name__ == "__main__":
    main()
