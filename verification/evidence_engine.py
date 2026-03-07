import chromadb
from chromadb.utils import embedding_functions

# Reuse the same embedding function
ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path="./data/vector_storage")
collection = client.get_or_create_collection(name="news_evidence", embedding_function=ef)

def find_evidence(query_text, top_k=5):
    # Query by semantic similarity
    results = collection.query(
        query_texts=[query_text],
        n_results=top_k
    )

    evidence = []
    # results['distances'] tells us how 'far' the match is (0 = identical)
    for i in range(len(results['documents'][0])):
        distance = results['distances'][0][i]
        
        # Convert distance to a similarity score (approximate)
        # Usually, a distance < 0.8 is a very strong match
        if distance < 1.0: 
            evidence.append({
                "title": results['documents'][0][i],
                "source": results['metadatas'][0][i]['source'],
                "url": results['metadatas'][0][i]['url'],
                "relevance": round((1 - distance) * 100, 2)
            })
            
    return evidence