from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

def TF_IDF(train_tokens, test_tokens):
    print("Preprocessing: Converting tokens to strings for TF-IDF...")
    X_train_text = [" ".join(tokens) for tokens in train_tokens]
    X_test_text = [" ".join(tokens) for tokens in test_tokens]

    # Initialize TF-IDF Vectorizer
    # Used standard english stop words to reduce noise
    vectorizer = TfidfVectorizer(lowercase=True, stop_words='english')
    # Fit the vectorizer on training data and transform both train and test data
    print("Extracting TF-IDF features...")
    X_train_tfidf = vectorizer.fit_transform(X_train_text)
    X_test_tfidf = vectorizer.transform(X_test_text)

    print(f"TF-IDF Matrix Shape (Train): {X_train_tfidf.shape}")
    return X_train_tfidf, X_test_tfidf, vectorizer

def inspect_data_length(tokens, dataset_name):
    # cal len
    lengths = [len(seq) for seq in tokens]
    
    # find the 95% length
    max_len = np.max(lengths)
    min_len = np.min(lengths)
    avg_len = np.mean(lengths)
    p95_len = np.percentile(lengths, 95)
    p99_len = np.percentile(lengths, 99) 

    print(f"--- {dataset_name} Data Length Statistics ---")
    print(f"Total samples: {len(lengths)}")
    print(f"Max Length:    {max_len}")
    print(f"Min Length:    {min_len}")
    print(f"Avg Length:    {avg_len:.2f}")
    print(f"95th %ile:     {p95_len} ")
    print(f"99th %ile:     {p99_len}")
    print("-" * 40)
    
    return int(p95_len) 

UNK = '<UNK>'
PAD = '<PAD>'

# build vocabulary
def build_vocab(tokens, freq_thres=2):
    # counting token frequency
    word_freq = {}
    for words in tokens:
        for word in words:
            if word in word_freq:
                word_freq[word] += 1
            else:
                word_freq[word] = 1

    vocab_idx = {}
    vocab_idx[UNK] = 0  # unknowns during training
    vocab_idx[PAD] = 1  # paddings

    # filter by frequency threshold
    while (len(word_freq) > 0):
        # find most freq token
        top_word = max(word_freq, key=lambda k: word_freq[k])

        if word_freq[top_word] < freq_thres: break

        word_freq.pop(top_word)
        vocab_idx[top_word] = len(vocab_idx)

    return vocab_idx

# padding
def pad_tokens(tokens, padding):
    padded_tokens = []

    for token in tokens:
        #adding the copy token incase change the original token
        new_token = token.copy()

        if len(new_token) > padding: # crop
            new_token = new_token[:padding]
        elif len(new_token) < padding: # pad
            new_token.extend([PAD] * (padding - len(new_token)))
        padded_tokens.append(new_token)

    return padded_tokens

# create intent map/idx
def intent_map(intents):
    intent_idx = {}
    for intent in intents:
        if not (intent in intent_idx):
            intent_idx[intent] = len(intent_idx)
    return intent_idx

# intents -> labels (one-hot vector)
def intent2label(intent_idx, intents):
    labels = []
    num_class = len(intent_idx)
    for intent in intents:
        label = [0] * num_class
        label[intent_idx[intent]] = 1
        labels.append(label)
    return labels

# labels -> intents
def label2intent(idx_intent, labels):
    intents = []
    for label in labels:
        idx = label.index(max(label))
        intents.append(idx_intent[idx])
    return intents

# words -> idx (numeric for training)
def token2idx(vocab_idx, tokens):
    data = []
    for token in tokens:
        idx = []
        for vocab in token:
            if vocab in vocab_idx:
                idx.append(vocab_idx[vocab])
            else:
                idx.append(vocab_idx[UNK])  # unknown (in test data)
        data.append(idx)
    return data


def LSTM_data_preprocessing(train_tokens,train_intent, train_avg_tokens, test_tokens, test_intent):

    # build vocab
    vocab_idx = build_vocab(train_tokens)
    vocab_size=len(vocab_idx)
    idx_vocab = { v: k for k, v in vocab_idx.items()}
    print(f"Built vocabularies: {len(vocab_idx)}")
    #padding/cropping
    padding=inspect_data_length(tokens=train_tokens, dataset_name="Training Dataset")
    #padding = train_avg_tokens
    print(f"Token padding length: {padding}")
    padded_train_tokens = pad_tokens(train_tokens, padding)
    padded_test_tokens = pad_tokens(test_tokens, padding)
    # intents -> labels
    intent_idx = intent_map(train_intent + test_intent)
    num_classes = len(intent_idx)
    idx_intent = { v: k for k, v in intent_idx.items()}
    #added the class name for plot
    class_names = [idx_intent[i] for i in range(num_classes)]

    print(f"Number of classes (intents): {len(intent_idx)}")
    #label is index!
    train_label = [intent_idx[i] for i in train_intent]
    test_label = [intent_idx[i] for i in test_intent]  

    #one-hot vector
    # train_label = intent2label(intent_idx, train_intent)
    # test_label = intent2label(intent_idx, test_intent)

    # tokens -> data (vectors for training)
    train_data = token2idx(vocab_idx, padded_train_tokens)
    test_data = token2idx(vocab_idx, padded_test_tokens)
    print()
    
    return train_data, train_label, test_data, test_label, vocab_size, num_classes, idx_intent, vocab_idx, class_names
