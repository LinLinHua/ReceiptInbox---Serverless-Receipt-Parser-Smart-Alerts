import numpy as np
from load_data import load_data
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, classification_report, confusion_matrix
import matplotlib.pyplot as plt
from sklearn.model_selection import learning_curve
import joblib
import os
import seaborn as sns
import pandas as pd

def logistic_regression(X_train_tfidf,X_test_tfidf,test_intents, train_intents,OUTPUT_DIR, vectorizer ):
    print("Training Logistic Regression Baseline...")
    
    # 'liblinear' solver is good for smaller datasets; max_iter increased for convergence
    # clf = LogisticRegression(random_state=42, solver='liblinear', max_iter=2000)
    # 'lbfgs' is more suitable for multiclass classification?
    clf = LogisticRegression(random_state=42, solver='lbfgs', max_iter=2000)
    
    # Scikit-learn handles string labels automatically, no need one-hot encode
    clf.fit(X_train_tfidf, train_intents)

    # ------Evaluation-----
    print("Evaluating model...")
    y_pred = clf.predict(X_test_tfidf)

    # Macro F1-Score due to class imbalance.
    acc = accuracy_score(test_intents, y_pred)
    macro_f1 = f1_score(test_intents, y_pred, average='macro')

    print("\n" + "="*40)
    print(" BASELINE RESULTS (Logistic Regression)")
    print("="*40)
    print(f"Accuracy: {acc:.4f}")
    print(f"Macro F1: {macro_f1:.4f}")
    print("-" * 40)
    
    # Detailed report to analyze failure modes for semantically similar classes
    print("\nClassification Report:")
    print(classification_report(test_intents, y_pred, zero_division=0))

    #save the model
    print(f"Saving model artifacts to {OUTPUT_DIR}...")
    
    model_path = os.path.join(OUTPUT_DIR, "logistic_model.pkl")
    vectorizer_path = os.path.join(OUTPUT_DIR, "tfidf_vectorizer.pkl")
    
    joblib.dump(clf, model_path)
    joblib.dump(vectorizer, vectorizer_path)
    print("Model and Vectorizer saved successfully.")

    return clf, y_pred , acc, macro_f1

def plot_learning_curve(estimator, X, y, title, OUTPUT_DIR):
    """
    Generates a plot showing the training and cross-validation scores
    as the number of training samples increases.
    """
    print(f"Generating learning curve for {title}...")
    
    # Define the sizes of the training set to evaluate (from 10% to 100%)
    train_sizes = np.linspace(0.1, 1.0, 5)
    
    # Compute learning curve values
    # cv=5: 5-fold Cross-Validation
    # scoring='f1_macro': Aligning with the proposal's priority on Macro F1
    train_sizes, train_scores, test_scores = learning_curve(
        estimator, X, y, cv=5, n_jobs=1, 
        train_sizes=train_sizes, scoring='f1_macro'
    )
    
    # Calculate mean and standard deviation for plotting error bands
    train_scores_mean = np.mean(train_scores, axis=1)
    train_scores_std = np.std(train_scores, axis=1)
    test_scores_mean = np.mean(test_scores, axis=1)
    test_scores_std = np.std(test_scores, axis=1)
    
    # Plotting
    plt.figure(figsize=(10, 6))
    plt.title(title)
    plt.xlabel("Training examples")
    plt.ylabel("Macro F1-Score")
    
    # Plot training scores (Red)
    plt.fill_between(train_sizes, train_scores_mean - train_scores_std,
                     train_scores_mean + train_scores_std, alpha=0.1, color="r")
    plt.plot(train_sizes, train_scores_mean, 'o-', color="r", label="Training score")
    
    # Plot cross-validation scores (Green)
    plt.fill_between(train_sizes, test_scores_mean - test_scores_std,
                     test_scores_mean + test_scores_std, alpha=0.1, color="g")
    plt.plot(train_sizes, test_scores_mean, 'o-', color="g", label="Cross-validation score")
    
    plt.grid()
    plt.legend(loc="best")
    plt.tight_layout()
    print("Learning curve generated.")
    #save the img
    filename="logistic_regression_LR.png"
    save_path = os.path.join(OUTPUT_DIR, filename)
    plt.savefig(save_path)
    print(f"Learning curve saved to {save_path}")
    #plt.show()

    return train_sizes, train_scores, test_scores

# 新增這個畫圖函式
def logistic_regression_confusion_matrix(y_true, y_pred, classes):
    print("Generating Confusion Matrix...")
    
    #cal cm
    cm = confusion_matrix(y_true, y_pred, labels=classes)
    df_cm = pd.DataFrame(cm, index=classes, columns=classes)
    
    plt.figure(figsize=(12, 10))
    sns.heatmap(df_cm, annot=True, fmt='d', cmap='Blues')
    
    plt.title('Baseline Confusion Matrix (Logistic Regression)')
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.xticks(rotation=90)
    plt.yticks(rotation=0)
    plt.tight_layout()
    
    # plt.show() 
