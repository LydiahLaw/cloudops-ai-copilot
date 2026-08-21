import os
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUNBOOKS_DIR = os.path.join(BASE_DIR, "..", "runbooks")
CHROMA_DIR = os.path.join(BASE_DIR, "..", "chroma_db")
EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = "qwen2.5:1.5b-instruct"

def load_and_split_documents():
    loader = DirectoryLoader(RUNBOOKS_DIR, glob="*.md", loader_cls=TextLoader)
    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "]
    )
    chunks = splitter.split_documents(documents)

    # attach clean source filename as metadata
    for chunk in chunks:
        source_path = chunk.metadata.get("source", "")
        chunk.metadata["source"] = os.path.basename(source_path)

    return chunks

def build_vectorstore(chunks):
    embeddings = OllamaEmbeddings(model=EMBED_MODEL)
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DIR
    )
    return vectorstore

def get_vectorstore():
    embeddings = OllamaEmbeddings(model=EMBED_MODEL)
    if os.path.exists(CHROMA_DIR):
        return Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
    chunks = load_and_split_documents()
    return build_vectorstore(chunks)

MIN_RELEVANCE = 0.55

def retrieve(query, k=2, score_threshold=MIN_RELEVANCE):
    vectorstore = get_vectorstore()
    results = vectorstore.similarity_search_with_relevance_scores(query, k=k)
    relevant = [(doc, score) for doc, score in results if score >= score_threshold]
    return relevant

if __name__ == "__main__":
    test_queries = [
        "Alloy cannot send logs to Loki, getting 404",
        "pod keeps restarting with CrashLoopBackOff",
        "seeing repeated failed SSH login attempts from one IP",
        "what's the best pizza topping combination"  # unsupported / fallback test
    ]

    for test_query in test_queries:
        results = retrieve(test_query)
        print(f"\n{'='*60}")
        print(f"Query: {test_query}\n")
        if not results:
            print("No relevant runbook found above threshold.")
        for doc, score in results:
            print(f"Source: {doc.metadata['source']} | Score: {score:.3f}")
            print(f"Content: {doc.page_content[:100]}...\n")