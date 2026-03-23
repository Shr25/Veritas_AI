import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer
import os

# Global variables (lazy initialization)
model = None
index = None
texts = None


def init_dataset():
    global model, index, texts

    if model is None:
        print("Loading embedding model...")
        model = SentenceTransformer('all-MiniLM-L6-v2')

    if index is None:
        if os.path.exists("data/clean_articles.csv"):
            print("Loading dataset...")
            df = pd.read_csv("data/clean_articles.csv")

            if "clean" not in df.columns:
                print("'clean' column missing in dataset")
                return

            texts = df["clean"].dropna().tolist()

            if not texts:
                print("No valid text data found")
                return

            print("Creating embeddings...")
            embeddings = model.encode(texts, batch_size=32, show_progress_bar=True)

            print("Building FAISS index...")
            index = faiss.IndexFlatL2(embeddings.shape[1])
            index.add(embeddings)

            print("Dataset ready")
        else:
            print("Dataset file not found")


def search_dataset(query):
    global model, index, texts

    # Initialize if not already done
    init_dataset()

    if model is None or index is None or texts is None:
        print("Dataset not initialized properly")
        return [], [0]

    try:
        print(f"Searching dataset for: {query}")

        q_vec = model.encode([query])
        D, I = index.search(q_vec, 3)

        results = [texts[i] for i in I[0] if i < len(texts)]
        scores = [float(1/(1+float(d))) for d in D[0]]

        print("Dataset search complete")

        return results, scores

    except Exception as e:
        print("Dataset search error:", e)
        return [], [0]