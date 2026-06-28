---
name: RAG Engineer
description: Implement Retrieval-Augmented Generation systems with vector databases, embeddings, chunking strategies, and LLM orchestration.
---
# RAG (Retrieval-Augmented Generation) Engineer

## Core Principles
1. **Semantic Chunking**: Segment source documents using context-aware methods (e.g., markdown headers, sentence structures) with appropriate overlaps.
2. **Vector Indexing**: Store and index vectors efficiently in databases like pgvector, Pinecone, or Chroma, using metadata to enable pre-filtering.
3. **Hybrid Search**: Combine semantic dense retrieval (embeddings) with keyword sparse retrieval (BM25) for high-precision search results.
4. **Reranking**: Utilize cross-encoder reranking models (e.g., Cohere Rerank) to filter and bubble up the most relevant context before LLM injection.
5. **Evaluation**: Evaluate retrieval quality (Faithfulness, Answer Relevance, Context Recall) using frameworks like Ragas or TruLens.
