import sys
import json

#for glove
import torch
import numpy as np

def load_data(fname):
    # read data file
    try:
        with open(fname, 'r') as file:
            raw_data = json.load(file)
            samples = raw_data['rasa_nlu_data']['common_examples']
    except Exception as e:
        print(str(e))
        sys.exit(1)

    # word-level tokenization
    data_tokens = []
    data_intent = []
    max_token = 0
    min_token = 50

    for sample in samples:
        data_intent.append(sample['intent'])
        text = sample['text']

        tokens = [word for word in text.lower().split()]        
        data_tokens.append(tokens)

        if len(tokens) > max_token: max_token = len(tokens)
        if len(tokens) < min_token: min_token = len(tokens)
    
    # average of max and min number of tokens
    avg_tokens = int((max_token + min_token) / 2)

    return data_tokens, data_intent, avg_tokens

# load GloVe data for pre-trined dic model
def load_glove_embeddings( word2idx, embedding_dim=100):
    path="../data/glove.6B.100d.txt"
    print(f"Loading GloVe embeddings from {path}...")
    
    embeddings_index = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            values = line.split()
            
            # check the dimention: vocabulary (1) + embedding_dim
            if len(values) != embedding_dim + 1:
                continue
            
            word = values[0]
            
            # loaded the word in our dataset
            if word in word2idx:
                try:
                    # transfer to float
                    coefs = np.asarray(values[1:], dtype='float32')
                    embeddings_index[word] = coefs
                except ValueError:
                    continue

    print(f"Found {len(embeddings_index)} relevant word vectors in GloVe.")

    # Build Embedding Matrix (init=normal distribution)
    vocab_size = len(word2idx)
    # set scale=0.6
    embedding_matrix = np.random.normal(scale=0.6, size=(vocab_size, embedding_dim))
    
    hits = 0
    misses = 0

    # fill in the vector in this dic
    for word, i in word2idx.items():
        embedding_vector = embeddings_index.get(word)
        if embedding_vector is not None:
            embedding_matrix[i] = embedding_vector
            hits += 1
        else:
            misses += 1
            
    print(f"Converted {hits} words ({hits/vocab_size:.1%}) from GloVe. Missed {misses} words.")
    
    return torch.from_numpy(embedding_matrix).float()