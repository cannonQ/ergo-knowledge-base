import * as lancedb from "@lancedb/lancedb";
import OpenAI from "openai";
import path from "path";

const VECTORDB_PATH = path.join(process.cwd(), "..", "vectordb");
const TABLE_NAME = "ekb_chunks";
const EMBED_MODEL = "text-embedding-3-small";
const EMBED_DIM = 1024;

let dbConnection: lancedb.Connection | null = null;
let openaiClient: OpenAI | null = null;

async function getDb(): Promise<lancedb.Connection> {
  if (!dbConnection) {
    dbConnection = await lancedb.connect(VECTORDB_PATH);
  }
  return dbConnection;
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

async function embedQuery(query: string): Promise<number[]> {
  const client = getOpenAI();
  const response = await client.embeddings.create({
    model: EMBED_MODEL,
    input: query,
    dimensions: EMBED_DIM,
  });
  return response.data[0].embedding;
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
  const db = await getDb();
  const table = await db.openTable(TABLE_NAME);
  const queryVector = await embedQuery(query);

  let search = table.search(queryVector).limit(limit * 2); // over-fetch for filtering

  const results = await search.toArray();

  let filtered = results.map((r: Record<string, unknown>) => ({
    file_path: r.file_path as string,
    title: r.title as string,
    category: r.category as string,
    project: r.project as string,
    tags: r.tags as string,
    text: r.text as string,
    tokens: r.tokens as number,
    _distance: r._distance as number,
  }));

  // Filter by category if specified
  if (category) {
    filtered = filtered.filter(
      (r) => r.category.toLowerCase() === category.toLowerCase()
    );
  }

  // Deduplicate by file_path (keep best chunk per doc)
  const seen = new Set<string>();
  const deduped: SearchResult[] = [];
  for (const r of filtered) {
    if (!seen.has(r.file_path) && deduped.length < limit) {
      seen.add(r.file_path);
      deduped.push(r);
    }
  }

  return deduped;
}

export async function listProjects(): Promise<
  { project: string; title: string; category: string; file_path: string }[]
> {
  const db = await getDb();
  const table = await db.openTable(TABLE_NAME);
  const all = await table.search([0]).limit(5000).toArray();

  // Get unique projects from chunk_index 0 (first chunk = overview)
  const projects = new Map<
    string,
    { project: string; title: string; category: string; file_path: string }
  >();

  for (const r of all as Record<string, unknown>[]) {
    const project = r.project as string;
    if (project && !projects.has(project)) {
      projects.set(project, {
        project,
        title: r.title as string,
        category: r.category as string,
        file_path: r.file_path as string,
      });
    }
  }

  return Array.from(projects.values()).sort((a, b) =>
    a.project.localeCompare(b.project)
  );
}
