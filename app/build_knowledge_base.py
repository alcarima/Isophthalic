from pathlib import Path
import chromadb
import ollama


# =========================================================
# CONFIGURATION
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge_base"
VECTOR_DB_DIR = BASE_DIR / "vector_db"

COLLECTION_NAME = "glass_plant_knowledge"
EMBEDDING_MODEL = "mxbai-embed-large"


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def read_markdown_files(folder: Path):
    """
    Read all .md files from the knowledge_base folder and subfolders.
    """
    documents = []

    for file_path in folder.rglob("*.md"):
        text = file_path.read_text(encoding="utf-8").strip()

        if not text:
            continue

        documents.append({
            "path": str(file_path),
            "relative_path": str(file_path.relative_to(folder)),
            "text": text,
            "section": file_path.parent.name,
            "filename": file_path.name,
        })

    return documents


def split_text(text: str, max_chars: int = 1500):
    """
    Simple text splitter.
    For the first version this is enough.
    """
    chunks = []
    current = ""

    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()

        if not paragraph:
            continue

        if len(current) + len(paragraph) > max_chars:
            chunks.append(current.strip())
            current = paragraph
        else:
            current += "\n\n" + paragraph

    if current.strip():
        chunks.append(current.strip())

    return chunks


def get_embedding(text: str):
    """
    Generate embedding using Ollama.
    """
    response = ollama.embed(
        model=EMBEDDING_MODEL,
        input=text
    )

    return response["embeddings"][0]


# =========================================================
# MAIN
# =========================================================

def main():
    print("Reading markdown documents...")

    documents = read_markdown_files(KNOWLEDGE_DIR)

    if not documents:
        print("No .md documents found in knowledge_base.")
        return

    print(f"Found {len(documents)} markdown documents.")

    client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))

    # Delete old collection if it exists, so we rebuild cleanly
    try:
        client.delete_collection(COLLECTION_NAME)
        print("Old collection deleted.")
    except Exception:
        pass

    collection = client.create_collection(name=COLLECTION_NAME)

    ids = []
    texts = []
    embeddings = []
    metadatas = []

    chunk_counter = 0

    for doc in documents:
        chunks = split_text(doc["text"])

        for i, chunk in enumerate(chunks):
            chunk_id = f"chunk_{chunk_counter:05d}"

            ids.append(chunk_id)
            texts.append(chunk)
            embeddings.append(get_embedding(chunk))
            metadatas.append({
                "source": doc["relative_path"],
                "section": doc["section"],
                "filename": doc["filename"],
                "chunk_number": i,
            })

            chunk_counter += 1

            print(f"Embedded {chunk_id} from {doc['relative_path']}")

    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    print("\nKnowledge base created successfully.")
    print(f"Documents: {len(documents)}")
    print(f"Chunks: {len(texts)}")
    print(f"Vector DB folder: {VECTOR_DB_DIR}")


if __name__ == "__main__":
    main()