import torch
import torch.nn as nn
from torch.utils.data import Dataset
from sklearn.metrics import f1_score, accuracy_score
import numpy as np
from matplotlib import pyplot as plt

#for confusion matrix
from sklearn.metrics import confusion_matrix
import seaborn as sns
import pandas as pd


class ATISDataset(Dataset):
    def __init__(self, features, labels):
        self.features = torch.LongTensor(features)# features: [N, Seq_Len]
        self.labels = torch.LongTensor(labels)# labels:[N] (index)

    def __len__(self):
        return len(self.features)

    def __getitem__(self, idx):
        return self.features[idx], self.labels[idx]

class LSTMClassifier(nn.Module):
    def __init__(self, vocab_size, embed_dim, hidden_dim, output_dim, n_layers=1, dropout=0.5):
        super(LSTMClassifier, self).__init__()
        
        # Layer 1: Learned Embeddings 
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=1)
        
        # Layer 2: LSTM
        self.lstm = nn.LSTM(
            input_size=embed_dim, 
            hidden_size=hidden_dim, 
            num_layers=n_layers, 
            batch_first=True, # input: (batch, seq, feature)
            dropout=dropout if n_layers > 1 else 0
        )
        
        # Layer 3: Linear Classifier
        self.fc = nn.Linear(hidden_dim, output_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, text):
        # 1. Embedding Look-up
        embedded = self.dropout(self.embedding(text))# text shape: [batch_size, seq_len]
        
        # 2. LSTM Forward Pass
        # (hidden, cell): the last hidden state
        output, (hidden, cell) = self.lstm(embedded)# output: a list of hidden state
        
        # hidden shape: [n_layers, batch_size, hidden_dim]
        last_hidden = hidden[-1]
        
        # 3. Final Prediction
        logits = self.fc(self.dropout(last_hidden))
        return logits

def evaluate(model, iterator, criterion, device):
    model.eval() # no dropout
    epoch_loss = 0
    all_preds = []
    all_labels = []
    
    with torch.no_grad():#evaluate no need gradient update
        for text, labels in iterator:
            text, labels = text.to(device), labels.to(device)
            predictions = model(text)
            loss = criterion(predictions, labels)
            epoch_loss += loss.item()
            
            # preditction=max(index)
            preds = predictions.argmax(dim=1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
            
    acc = accuracy_score(all_labels, all_preds)
    f1 = f1_score(all_labels, all_preds, average='macro')
    
    return epoch_loss / len(iterator), acc, f1

def plot_training_history(train_losses, val_losses, val_f1s):
    epochs = range(1, len(train_losses) + 1)

    plt.figure(figsize=(12, 5))

    # Loss Curve
    plt.subplot(1, 2, 1)
    plt.plot(epochs, train_losses, 'b-o', label='Training Loss')
    plt.plot(epochs, val_losses, 'r-o', label='Validation Loss')
    plt.title('Training & Validation Loss')
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.legend()
    plt.grid(True)

    # Macro F1 Score
    plt.subplot(1, 2, 2)
    plt.plot(epochs, val_f1s, 'g-o', label='Validation Macro F1')
    plt.title('Validation Macro F1-Score')
    plt.xlabel('Epochs')
    plt.ylabel('F1 Score')
    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    
def plot_confusion_matrix(model, iterator, device, classes):
    model.eval()
    all_preds = []
    all_labels = []
    
    with torch.no_grad():
        for text, labels in iterator:
            text, labels = text.to(device), labels.to(device)
            predictions = model(text)
            preds = predictions.argmax(dim=1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
    
    # cal cm
    num_classes = len(classes) #in case the test set doesn't show all classes
    cm = confusion_matrix(all_labels, all_preds, labels=range(num_classes))
    
    # plot
    plt.figure(figsize=(12, 10))
    df_cm = pd.DataFrame(cm, index=classes, columns=classes)
    
    sns.heatmap(df_cm, annot=True, fmt='d', cmap='Blues')
    plt.title('Confusion Matrix')
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.xticks(rotation=90)
    plt.yticks(rotation=0)
    plt.tight_layout()
    
    # plt.show()