from pathlib import Path
import chromadb
import ollama


# =========================================================
# CONFIGURATION
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
VECTOR_DB_DIR = BASE_DIR / "vector_db"

COLLECTION_NAME = "glass_plant_knowledge"
EMBEDDING_MODEL = "mxbai-embed-large"
LLM_MODEL = "llama3.1:8b"


# =========================================================
# FUNCTIONS
# =========================================================

def get_embedding(text: str):
    response = ollama.embed(
        model=EMBEDDING_MODEL,
        input=text
    )
    return response["embeddings"][0]


def retrieve_relevant_docs(question: str, n_results: int = 5):
    client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
    collection = client.get_collection(name=COLLECTION_NAME)

    question_embedding = get_embedding(question)

    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=n_results,
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    retrieved = []

    for doc, meta in zip(documents, metadatas):
        retrieved.append({
            "text": doc,
            "source": meta.get("source", "unknown"),
            "section": meta.get("section", "unknown"),
        })

    return retrieved


def build_prompt(question: str, current_values: dict, retrieved_docs: list):
    docs_text = ""

    for i, item in enumerate(retrieved_docs, start=1):
        docs_text += f"\n--- DOCUMENT {i} ---\n"
        docs_text += f"Source: {item['source']}\n"
        docs_text += f"Section: {item['section']}\n"
        docs_text += item["text"]
        docs_text += "\n"

    values_text = "\n".join(
        f"- {key}: {value}" for key, value in current_values.items()
    )

    prompt = f"""
You are the Operator Suggestion Assistant for the Glass Plant.

Your task is to support a process operator.

Rules:
- Use only the current process data and the retrieved documentation.
- Do not invent plant procedures.
- Do not suggest actions that are not supported by the documentation.
- If the documentation is insufficient, say clearly: "Insufficient documented basis."
- Keep the answer practical and operator-oriented.
- Always include a safety note when the condition may be process-safety relevant.
- The calculated status provided in the current process data is authoritative.
- Do not contradict the calculated status.
- If a value is within its stated normal range, do not describe it as high or low.

Current process data:
{values_text}

Operator question:
{question}

Retrieved documentation:
{docs_text}

Please answer using this structure:

OPERATOR SUGGESTION

1. Situation summary
2. Most likely causes
3. Operator checks
4. Suggested corrective actions
5. Safety / process safety note
6. Documentation used
7. Confidence: High / Medium / Low
"""

    return prompt


def ask_ollama(prompt: str):
    response = ollama.chat(
        model=LLM_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        options={
            "temperature": 0.2
        }
    )

    return response["message"]["content"]

# =========================================================

# MAIN FUNCTION USED BY TKINTER

# =========================================================

def generate_operator_suggestion(current_values: dict, question: str) -> str:

    """

    Generate an operator suggestion using:

    - current process values from the Tkinter model

    - relevant documents retrieved from the vector database

    - Ollama local model

    """

    try:

        retrieved_docs = retrieve_relevant_docs(question, n_results=5)

        prompt = build_prompt(

            question=question,

            current_values=current_values,

            retrieved_docs=retrieved_docs

        )

        answer = ask_ollama(prompt)

        return answer

    except Exception as e:

        return f"AI Operator Suggestion error:\n{e}"
# =========================================================
# TEST CASE
# =========================================================

def main():
    current_values = {
        "Oxygen in offgas": "High deviation",
        "Thick indicator": "0.34 - NOT OK",
        "Reactor pressure": "15.2 barg",
        "Reactor temperature": "188.5 °C",
        "MX conversion": "0.966",
    }

    question =  """

Review the current PTA / isophthalic reactor process state.

Provide operator guidance based on:

- current calculated process values,

- calculated status values,

- retrieved operating notes and best practices.

Rules:

- Treat the calculated status values as authoritative.

- Do not describe a value as high, low, warning, or abnormal if its calculated status is OK.

- Focus only on items that are not OK, are close to limits, or require routine operator awareness.

- If all main indicators are OK, say that no immediate corrective action is required.

"""

    print("Retrieving relevant documents...")
    retrieved_docs = retrieve_relevant_docs(question, n_results=5)

    print("\nRetrieved sources:")
    for item in retrieved_docs:
        print("-", item["source"])

    prompt = build_prompt(question, current_values, retrieved_docs)

    print("\nAsking Ollama...\n")
    answer = ask_ollama(prompt)

    print(answer)


if __name__ == "__main__":
    main()
