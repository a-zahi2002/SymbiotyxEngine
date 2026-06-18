"""
train_gesture_model.py
----------------------
Improved training script for the LSTM gesture classifier.
Includes validation split, early stopping, best checkpoint saving,
confusion matrix evaluation, and training logs.
"""

import os
import sys
import json
import glob
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader, random_split
from sklearn.metrics import confusion_matrix, classification_report

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.models.gesture_classifier import GestureClassifier, save_model

DATA_RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
DATA_PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")

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

def load_dataset():
    """
    Loads JSON files, processes, and builds the dataset.
    """
    print("[INFO] Loading and processing dataset...")
    X, y = [], []
    class_names = []
    
    # Load from raw directory and processed directory
    for base_dir in [DATA_RAW_DIR, DATA_PROCESSED_DIR]:
        if not os.path.exists(base_dir): continue
        for user_folder in os.listdir(base_dir):
            user_path = os.path.join(base_dir, user_folder)
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

    if not X:
        print("[WARN] No valid data found in raw or processed directories.")
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
    
    # 1. Validation Split (80% Train, 20% Val)
    val_size = int(len(dataset) * 0.2)
    train_size = len(dataset) - val_size
    train_dataset, val_dataset = random_split(dataset, [train_size, val_size])
    
    train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=16, shuffle=False)
    
    num_classes = len(class_map)
    model = GestureClassifier(input_dim=FEATURE_DIM, num_classes=num_classes)
    
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    # Early Stopping parameters
    epochs = 100
    patience = 10
    best_val_loss = float("inf")
    epochs_no_improve = 0
    best_model_state = None
    
    # Logging configuration
    log_filepath = os.path.join(SCRIPT_DIR, "training_log.txt")
    log_file = open(log_filepath, "w", encoding="utf-8")
    log_file.write(f"Training Log - Classes: {class_map}\n")
    log_file.write("Epoch,TrainLoss,TrainAcc,ValLoss,ValAcc\n")
    
    print(f"[INFO] Started Training on classes: {class_map}")
    for epoch in range(epochs):
        # --- Training ---
        model.train()
        train_loss = 0
        train_correct = 0
        train_total = 0
        for batch_X, batch_y in train_loader:
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            train_total += batch_y.size(0)
            train_correct += (predicted == batch_y).sum().item()
            
        train_loss /= len(train_loader)
        train_acc = 100. * train_correct / train_total

        # --- Validation ---
        model.eval()
        val_loss = 0
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for batch_X, batch_y in val_loader:
                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)
                val_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                val_total += batch_y.size(0)
                val_correct += (predicted == batch_y).sum().item()
                
        val_loss /= len(val_loader) if len(val_loader) > 0 else 1
        val_acc = 100. * val_correct / val_total if val_total > 0 else 0

        # Log epoch results
        log_file.write(f"{epoch+1},{train_loss:.4f},{train_acc:.2f},{val_loss:.4f},{val_acc:.2f}\n")
        
        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(f"Epoch {epoch+1:02d} | Train Loss: {train_loss:.4f} Acc: {train_acc:.1f}% | Val Loss: {val_loss:.4f} Acc: {val_acc:.1f}%")
            
        # Early stopping and checkpointing check
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            epochs_no_improve = 0
            best_model_state = model.state_dict().copy()
            # Save temporary best checkpoint
            torch.save(best_model_state, os.path.join(SCRIPT_DIR, "gesture_model_checkpoint.pth"))
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= patience:
                print(f"[INFO] Early stopping triggered at epoch {epoch+1}. Best Val Loss: {best_val_loss:.4f}")
                log_file.write(f"Early stopping triggered at epoch {epoch+1}. Best Val Loss: {best_val_loss:.4f}\n")
                break

    log_file.close()

    # Load best model for evaluation and final save
    if best_model_state is not None:
        model.load_state_dict(best_model_state)

    # --- Final Evaluation & Confusion Matrix ---
    model.eval()
    all_preds = []
    all_targets = []
    with torch.no_grad():
        for batch_X, batch_y in val_loader:
            outputs = model(batch_X)
            _, predicted = torch.max(outputs.data, 1)
            all_preds.extend(predicted.cpu().numpy())
            all_targets.extend(batch_y.cpu().numpy())

    if all_targets:
        print("\n" + "="*40)
        print("  CLASSIFICATION REPORT")
        print("="*40)
        target_names = [class_map[i] for i in range(num_classes)]
        print(classification_report(all_targets, all_preds, target_names=target_names))
        
        print("\n" + "="*40)
        print("  CONFUSION MATRIX")
        print("="*40)
        cm = confusion_matrix(all_targets, all_preds)
        print("      " + " ".join([f"{name[:4]:>5}" for name in target_names]))
        for i, row in enumerate(cm):
            print(f"{target_names[i][:4]:>5} " + " ".join([f"{val:>5d}" for val in row]))
        print("="*40 + "\n")

    print("[INFO] Saving final model...")
    save_model(model, class_map)

if __name__ == "__main__":
    main()
