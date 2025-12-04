from load_data import load_data
from preprocess import TF_IDF
from logistic_regression import logistic_regression, plot_learning_curve, logistic_regression_confusion_matrix

#library for LSTM
import os
import torch
from torch.utils.data import DataLoader
import torch.nn as nn
import torch.optim as optim
from LSTM import LSTMClassifier, ATISDataset, evaluate, plot_training_history, plot_confusion_matrix
from preprocess import LSTM_data_preprocessing
from matplotlib import pyplot as plt

#library for GloVe
from load_data import load_glove_embeddings

DATA_TRAIN = "../data/train.json"
DATA_TEST = "../data/test.json"

FIGURE_DIR = "../output/figures"
MODEL_DIR = "../output/models"

def main():

    #---------------------------------- loading data ----------------------------------
    print("Loading data...")
    train_tokens, train_intent, train_avg_tokens = load_data(DATA_TRAIN)
    test_tokens, test_intent, test_avg_tokens = load_data(DATA_TEST)
    print(f"Loaded training samples: {len(train_tokens)}")
    print(f"Loaded testing samples: {len(test_tokens)}")
    print()


    #------------------------------ logistic regression ------------------------------
    # data preprocessing 
    print("Preprocessing data for logistic regression...")
    #preprocessing for TF-IDF
    X_train_tfidf, X_test_tfidf, vectorizer= TF_IDF(train_tokens, test_tokens)
    print("Preprocessing TF-IDF data completed...")

    # model
    clf, y_pred, acc, macro_f1 = logistic_regression(X_train_tfidf,X_test_tfidf,test_intent, train_intent, OUTPUT_DIR=MODEL_DIR, vectorizer=vectorizer )
    
    # plot learning curve
    train_sizes, train_scores, test_scores=plot_learning_curve(clf, X_train_tfidf, train_intent, "Logistic_Regression's Learning Curve", OUTPUT_DIR=FIGURE_DIR)
    logistic_regression_confusion_matrix(test_intent, y_pred, classes=clf.classes_)
    # save img
    save_path = os.path.join(FIGURE_DIR, "baseline_confusion_matrix.png")
    plt.savefig(save_path)
    print(f"Confusion Matrix saved to {save_path}")
    print()


    #----------------------------- Preprocessing for LSTM -----------------------------
    # data preprocessing 
    print("Preprocessing data for LSTM...")
    train_data, train_label, test_data, test_label, vocab_size, num_classes, idx_intent, vocab_idx, class_names = LSTM_data_preprocessing(train_tokens,train_intent, train_avg_tokens, test_tokens, test_intent)

    # setting device (cuda/mps/cpu)
    device = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Using device: {device}")

    # Build DataLoader
    BATCH_SIZE = 64
    train_dataset = ATISDataset(train_data, train_label)
    test_dataset = ATISDataset(test_data, test_label)
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)

    # Training method
    EPOCHS = 30

    def train(model, EPOCHS, optimizer, train_loader, test_loader, lr_scheduler=None):
        train_losses = []
        val_losses = []
        val_f1s = []

        criterion = nn.CrossEntropyLoss()

        print(f"\nStarting training for {EPOCHS} epochs...")
        for epoch in range(EPOCHS):
            model.train()
            epoch_loss = 0
            
            for text, labels in train_loader:
                text, labels = text.to(device), labels.to(device)
                
                optimizer.zero_grad()        # gradient=0
                predictions = model(text)    # Forward
                loss = criterion(predictions, labels) # Loss
                loss.backward()              # Backward
                optimizer.step()             # Update
                
                epoch_loss += loss.item()

            # evaluate
            avg_val_loss, val_acc, val_f1 = evaluate(model, test_loader, criterion, device)
            #record the train history
            avg_train_loss = epoch_loss / len(train_loader)
            train_losses.append(avg_train_loss)
            val_losses.append(avg_val_loss)
            val_f1s.append(val_f1)

            if lr_scheduler:
                lr_scheduler.step(avg_val_loss)
            
            print(f"Epoch: {epoch+1:02} | Train Loss: {epoch_loss/len(train_loader):.3f} | "
                f"Val Loss: {avg_val_loss:.3f} | Val Acc: {val_acc:.3f} | Val Macro F1: {val_f1:.3f}")
        
        return model, train_losses, val_losses, val_f1s


    #----------------------------- Experiement 3_a: LSTM -----------------------------
    print("\n" + "="*40)
    print(" EXPERIMENT 3A: LSTM ")
    print("="*40)

    # 1. Build model
    model = LSTMClassifier(vocab_size, embed_dim=128, hidden_dim=256, output_dim=num_classes)
    model = model.to(device)

    # 2. train
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    model, train_losses, val_losses, val_f1s = train(model, EPOCHS, optimizer, train_loader, test_loader)

    # 3. save model
    save_path = os.path.join(MODEL_DIR, "lstm_model.pt")
    torch.save(model.state_dict(), save_path)
    print(f"Model saved to {save_path}")

    # 4. Plot the learniung curve
    plot_training_history(train_losses, val_losses, val_f1s)
    # save img
    save_path = os.path.join(FIGURE_DIR, "lstm_learning_curve.png")
    plt.savefig(save_path)
    print(f"\nLearning curve saved to {save_path}")

    #plot confusion matrix
    plot_confusion_matrix(model, iterator=test_loader, device=device, classes=class_names)
    #save img
    save_path = os.path.join(FIGURE_DIR, "lstm_cm.png")
    plt.savefig(save_path)
    print(f"Confusion Matrix saved to {save_path}")
    # plt.show()
    print()


    #--------------------------- Experiment 3_b: LSTM+GloVe ---------------------------
    print("\n" + "="*40)
    print(" EXPERIMENT 3B: LSTM+GloVe ")
    print("="*40)

    # 1. Build model
    # Notice the glove's dimention=100 
    model = LSTMClassifier(len(vocab_idx), embed_dim=100, hidden_dim=256, output_dim=num_classes)
    
    # Experiment 3b：Initialize with GloVe vectors 
    embedding_matrix = load_glove_embeddings(vocab_idx, embedding_dim=100)
    model.embedding.weight.data.copy_(embedding_matrix)
    # model.embedding.weight.requires_grad = False
    model = model.to(device)

    # 2. train
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    model, train_losses, val_losses, val_f1s = train(model, EPOCHS, optimizer, train_loader, test_loader)

    # 3. save model
    save_path = os.path.join(MODEL_DIR, "lstmGloVe_model.pt")
    torch.save(model.state_dict(), save_path)
    print(f"Model saved to {save_path}")

    # 4. Plot the learniung curve
    plot_training_history(train_losses, val_losses, val_f1s)
    # save img
    save_path = os.path.join(FIGURE_DIR, "lstmGloVe_learning_curve.png")
    plt.savefig(save_path)
    print(f"\nLearning curve saved to {save_path}")

    #plot confusion matrix
    plot_confusion_matrix(model, iterator=test_loader, device=device, classes=class_names)
    #save img
    save_path = os.path.join(FIGURE_DIR, "lstmGloVe_cm.png")
    plt.savefig(save_path)
    print(f"Confusion Matrix saved to {save_path}")
    # plt.show()
    print()


    #-------------- Experiment 4: Systematic Hyperparameter Optimization --------------
    print("\n" + "="*40)
    print(" EXPERIMENT 4: LSTM+GloVe HYPERPARAMETERS TUNING ")
    print("="*40)

    # 1. Build model
    model = LSTMClassifier(len(vocab_idx), embed_dim=100, hidden_dim=256, output_dim=num_classes, dropout=0.4, n_layers=2)
    # Initialize with GloVe vectors 
    embedding_matrix = load_glove_embeddings(vocab_idx, embedding_dim=100)
    model.embedding.weight.data.copy_(embedding_matrix)
    model = model.to(device)

    # 2. train
    optimizer = optim.Adam(model.parameters(), lr=0.002)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.1, patience=5)
    EPOCHS = 30
    model, train_losses, val_losses, val_f1s = train(model, EPOCHS, optimizer, train_loader, test_loader, lr_scheduler=scheduler)

    # 3. save model
    save_path = os.path.join(MODEL_DIR, "lstmGloVe_model_opt.pt")
    torch.save(model.state_dict(), save_path)
    print(f"Model saved to {save_path}")

    # 4. Plot the learniung curve
    plot_training_history(train_losses, val_losses, val_f1s)
    # save img
    save_path = os.path.join(FIGURE_DIR, "lstmGloVe_learning_curve_opt.png")
    plt.savefig(save_path)
    print(f"\nLearning curve saved to {save_path}")

    #plot confusion matrix
    plot_confusion_matrix(model, iterator=test_loader, device=device, classes=class_names)
    #save img
    save_path = os.path.join(FIGURE_DIR, "lstmGloVe_cm_opt.png")
    plt.savefig(save_path)
    print(f"Confusion Matrix saved to {save_path}")
    # plt.show()

    """
    Experimented:
        dropout: 0.5, 0.4
        hidden_dim: 256, 128
        n_layers (LSTM): 1, 2, 3
        learning rate (initial): 0.05, 0.005, 0.002, 0.001, 0.0005
        learning rate scheduling: StepLR(optimizer, step_size=10, gamma=0.1), ReduceLROnPlateau(optimizer, mode='min', factor=0.1, patience=5)
        weight decay (L2): 0.0001
        batch size: 32, 64, 128
        epoch: 30, 40

    Best Results: 
        dropout: 0.4
        hidden_dim: 256
        n_layers (LSTM): 2
        learning rate (initial): 0.002
        learning rate scheduling: ReduceLROnPlateau(optimizer, mode='min', factor=0.1, patience=5)
        batch size: 64
        epoch: 30
    """

if __name__ == "__main__":
    main()