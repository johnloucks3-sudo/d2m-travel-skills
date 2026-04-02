# PINECONE VECTOR DATABASE INTEGRATION PLAN
**To:** Commander (Yoda)
**From:** Goose & A2 (Dembe)

## 1. THE DATA INGESTION (What we put in)
We will convert our flat Markdown files into "Vectors" (arrays of 1536 numbers) using an embedding model (like OpenAI's `text-embedding-3-small`).
*   **Target 1: Client Dossiers:** We chunk every dossier by section (Flights, Preferences, Insurance) and embed them.
*   **Target 2: Persistent Lessons:** We embed the `goose_persistent_lessons.md` rules so the system mathematically recalls your exact formatting constraints before drafting an email.
*   **Target 3: TESS Commission History:** We embed past pricing data so A5 (Castillo) can instantly recall historical margins for specific cruise lines.

## 2. THE ARCHITECTURE (How we query it)
When A3 (Dani) is asked to draft an email to the Furlows, she won't just guess their preferences. 
1.  **The Trigger:** Dani's prompt hits the `llm_query.ts` tool.
2.  **The Vector Search:** Before the LLM answers, the script takes Dani's question ("What are the Furlow's cruise preferences?") and embeds it into a vector.
3.  **The Query:** We query your Pinecone `quickstart` index with that vector. Pinecone instantly returns the top 3 most mathematically relevant chunks of text from the dossiers.
4.  **The Synthesis:** Those 3 chunks are injected invisibly into Dani's context window. She writes the perfect email.

## 3. IMPLEMENTATION STEPS (The Roadmap)
1.  **Generate Embeddings:** I need authorization to use the OpenAI API key (or DeepSeek/Gemini) to generate the actual vector embeddings for our files.
2.  **Write the Ingest Script:** I will build `pinecone_ingest.py` to chunk the `/home/john/Thunderbird/dossiers/` directory and push it to the index.
3.  **Update the Model Router:** I will modify `thunderbird_model_router.py` so that every prompt automatically checks Pinecone for relevant context *before* hitting the LLM.