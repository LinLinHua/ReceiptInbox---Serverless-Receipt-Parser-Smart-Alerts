# Intent Classification for Natural Language Queries


This project implements a Deep Learning system to classify user queries into 26 intent categories using the **ATIS (Airline Travel Information System)** dataset. The system compares a machine learning baseline against various LSTM-based architectures to handle semantically similar intents and domain-specific vocabulary.

## Project Structure

```text
./
├── output/
│   └── figures/            # Learning curves and confusion matrices
├── src/
│   ├── load_data.py        # Data loading and GloVe parsing
│   ├── logistic_regression.py # Baseline model
│   ├── LSTM.py             # LSTM architecture definition
│   ├── preprocess.py       # Tokenization, padding, and indexing
│   └── train.py            # Main training script
├── log.txt                 # Training log
├── README.md
└── run.sh*                 # Train command
```

## Experiments
This project conducts a systematic investigation through the following experiments:

1.  **Baseline:** Logistic Regression with TF-IDF features (Scikit-learn).
2.  **Experiment 3a:** LSTM with **Learned Embeddings** (trained from scratch).
3.  **Experiment 3b:** LSTM with **Pre-trained GloVe Embeddings** (Transfer Learning).
4.  **Experiment 4:** Optimization (Multi-layer LSTM, Dropout tuning, Hyperparameter search).

## Setup & Installation

### 1. Prerequisites
Ensure you have Python 3.x installed with the following libraries:
```bash
pip install torch numpy pandas scikit-learn matplotlib seaborn
```

### 2. Data Setup (Important!)

1.  **ATIS_dataset:**

    **Download Link:** [https://github.com/howl-anderson/ATIS_dataset](https://github.com/howl-anderson/ATIS_dataset)

    (This project uses json format ATIS data, find and move `data/standard_format/rasa/train.json` and `data/standard_format/rasa/test.json` into the `data/` directory)
    
2.  **GloVe:**
    
    **Download Link:** [https://nlp.stanford.edu/data/wordvecs/glove.2024.wikigiga.100d.zip](https://nlp.stanford.edu/data/wordvecs/glove.2024.wikigiga.100d.zip)

    (Unzip and rename the data file as `glove.6B.100d.txt`, then move into the `data/` directory)

    *(Note: This project uses 100-dimensional vectors. Do not use 50d, 200d, or 300d files unless you modify the `EMBED_DIM` in the code.)*

## Usage

To train and evaluate the models:
```bash
chmod +x run.sh
./run.sh
```
This script will:
1.  Load and preprocess the ATIS data.
2.  Train and evaluate the Logistic Regression baseline
3.  Load the GloVe embeddings (if configured for Exp 3b/4).
4.  Train the LSTM model.
5.  Save the best model to `output/models/`.
6.  Generate Learning Curves and Confusion Matrices in `output/figures/`.
7.  Generate `log.txt` during training

## Evaluation Metrics
Since the ATIS dataset exhibits class imbalance, we prioritize **Macro F1-Score** alongside Accuracy to ensure the model performs well on rare classes.

---
**Course:** EE 541 - A Computational Introduction to Deep Learning

**Authors:** Harry Kang, Lin Lin Hua