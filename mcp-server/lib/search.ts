import OpenAI from "openai";
import fs from "fs";
import path from "path";

const DATA_DIR = path.join(process.cwd(), "data");
const EMBED_MODEL = "text-embedding-3-small";
const EMBED_DIM = 1024;

// In-memory index — loaded once on cold start
let vectors: Float32Array | null = null;
let metadata: ChunkMeta[] | null = null;
let openaiClient: OpenAI | null = null;

interface ChunkMeta {
  file_path: string;
  title: string;
  category: string;
  project: string;
  tags: string;
  text: string;
  tokens: number;
  chunk_index: number;
}

function loadIndex(): { vectors: Float32Array; metadata: ChunkMeta[] } {
  if (vectors && metadata) {
    return { vectors, metadata };
  }

  const vectorsBuf = fs.readFileSync(path.join(DATA_DIR, "vectors.bin"));
  vectors = new Float32Array(
    vectorsBuf.buffer,
    vectorsBuf.byteOffset,
    vectorsBuf.byteLength / 4
  );

  const metaJson = fs.readFileSync(
    path.join(DATA_DIR, "metadata.json"),
    "utf-8"
  );
  metadata = JSON.parse(metaJson);

  const numChunks = metadata!.length;
  console.log(`Loaded ${numChunks} chunks (${(vectorsBuf.byteLength / 1024 / 1024).toFixed(1)} MB vectors)`);

  return { vectors, metadata: metadata! };
}

function getOpenAI(): OpenAI {
  if (!openaiClient) {
    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) {
      throw new Error("OPENAI_API_KEY environment variable required");
    }
    openaiClient = new OpenAI({ apiKey });
  }
  return openaiClient;
}

async function embedQuery(query: string): Promise<Float32Array> {
  const client = getOpenAI();
  const response = await client.embeddings.create({
    model: EMBED_MODEL,
    input: query,
    dimensions: EMBED_DIM,
  });
  return new Float32Array(response.data[0].embedding);
}

/**
 * Cosine similarity between a query vector and the i-th stored vector.
 * Vectors are assumed to be normalized (OpenAI embeddings are unit-length).
 */
function cosineSim(
  query: Float32Array,
  allVectors: Float32Array,
  index: number
): number {
  const offset = index * EMBED_DIM;
  let dot = 0;
  for (let j = 0; j < EMBED_DIM; j++) {
    dot += query[j] * allVectors[offset + j];
  }
  return dot; // For unit vectors, dot product = cosine similarity
}

export interface SearchResult {
  file_path: string;
  title: string;
  category: string;
  project: string;
  tags: string;
  text: string;
  tokens: number;
  _distance: number;
}

export async function searchDocs(
  query: string,
  category?: string,
  limit: number = 5
): Promise<SearchResult[]> {
  const { vectors: vecs, metadata: meta } = loadIndex();
  const queryVec = await embedQuery(query);
  const numChunks = meta.length;

  // Compute similarities
  const scores: { index: number; sim: number }[] = new Array(numChunks);
  for (let i = 0; i < numChunks; i++) {
    scores[i] = { index: i, sim: cosineSim(queryVec, vecs, i) };
  }

  // Sort descending by similarity
  scores.sort((a, b) => b.sim - a.sim);

  // Filter by category if specified
  let candidates = scores;
  if (category) {
    candidates = scores.filter(
      (s) => meta[s.index].category.toLowerCase() === category.toLowerCase()
    );
  }

  // Deduplicate by file_path (keep best chunk per doc)
  const seen = new Set<string>();
  const results: SearchResult[] = [];
  for (const s of candidates) {
    const m = meta[s.index];
    if (!seen.has(m.file_path) && results.length < limit) {
      seen.add(m.file_path);
      results.push({
        file_path: m.file_path,
        title: m.title,
        category: m.category,
        project: m.project,
        tags: m.tags,
        text: m.text,
        tokens: m.tokens,
        _distance: 1 - s.sim, // Convert similarity to distance for compatibility
      });
    }
  }

  return results;
}

export async function listProjects(): Promise<
  { project: string; title: string; category: string; file_path: string }[]
> {
  const { metadata: meta } = loadIndex();

  const projects = new Map<
    string,
    { project: string; title: string; category: string; file_path: string }
  >();

  for (const m of meta) {
    if (m.project && !projects.has(m.project)) {
      projects.set(m.project, {
        project: m.project,
        title: m.title,
        category: m.category,
        file_path: m.file_path,
      });
    }
  }

  return Array.from(projects.values()).sort((a, b) =>
    a.project.localeCompare(b.project)
  );
}
