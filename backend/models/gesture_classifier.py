import torch
import torch.nn as nn
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

class GestureClassifier(nn.Module):
    """
    LSTM-based sequence classifier for gesture recognition.
    Expects input of shape: (batch_size, sequence_length, input_dim)
    """
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int = 64, num_layers: int = 2):
        super(GestureClassifier, self).__init__()
        self.input_dim = input_dim
        self.num_classes = num_classes
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers

        # LSTM Layer
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.2 if num_layers > 1 else 0.0
        )
        
        # Fully connected (classification) layer
        self.fc = nn.Linear(hidden_dim, num_classes)

    def forward(self, x):
        # x shape: (batch_size, seq_len, input_dim)
        lstm_out, (hn, cn) = self.lstm(x)
        
        # Get the output from the last time step
        # hn[-1] shape: (batch_size, hidden_dim)
        out = self.fc(hn[-1])
        return out

def save_model(model: nn.Module, class_map: dict, filepath: str = None):
    if filepath is None:
        filepath = os.path.join(SCRIPT_DIR, "gesture_model.pth")
    state = {
        "state_dict": model.state_dict(),
        "input_dim": model.input_dim,
        "num_classes": model.num_classes,
        "hidden_dim": model.hidden_dim,
        "num_layers": model.num_layers,
        "class_map": class_map
    }
    torch.save(state, filepath)
    print(f"[INFO] Model saved to {filepath}")

def load_model(filepath: str = None) -> tuple[nn.Module, dict]:
    if filepath is None:
        filepath = os.path.join(SCRIPT_DIR, "gesture_model.pth")
        
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"No trained model found at {filepath}")
        
    state = torch.load(filepath, map_location=torch.device('cpu'))
    
    model = GestureClassifier(
        input_dim=state["input_dim"],
        num_classes=state["num_classes"],
        hidden_dim=state["hidden_dim"],
        num_layers=state["num_layers"]
    )
    model.load_state_dict(state["state_dict"])
    model.eval()
    return model, state["class_map"]
