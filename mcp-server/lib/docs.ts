import fs from "fs";
import path from "path";

const CONTENT_DIR = path.join(process.cwd(), "..", "content");

function findFile(dir: string, name: string): string | null {
  const normalizedName = name.toLowerCase().replace(/[^a-z0-9-]/g, "-");

  try {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        const found = findFile(fullPath, name);
        if (found) return found;
      } else if (entry.isFile() && entry.name.endsWith(".md")) {
        const stem = entry.name.replace(/\.md$/, "").toLowerCase();
        if (
          stem === normalizedName ||
          stem === `overview_${normalizedName}` ||
          stem.includes(normalizedName)
        ) {
          return fullPath;
        }
      }
    }
  } catch {
    // Directory doesn't exist or isn't readable
  }
  return null;
}

export function getConcept(name: string): string | null {
  const conceptDir = path.join(CONTENT_DIR, "concepts");
  const filePath = findFile(conceptDir, name);
  if (filePath) {
    return fs.readFileSync(filePath, "utf-8");
  }
  return null;
}

export function getPattern(name: string): string | null {
  const patternDir = path.join(CONTENT_DIR, "patterns");
  const filePath = findFile(patternDir, name);
  if (filePath) {
    return fs.readFileSync(filePath, "utf-8");
  }
  return null;
}

export function getContract(
  project: string,
  contract?: string
): string | null {
  const ecosystemDir = path.join(CONTENT_DIR, "ecosystem");
  const projectDir = path.join(ecosystemDir, project);

  if (!fs.existsSync(projectDir)) {
    // Try fuzzy match on directory name
    const dirs = fs.readdirSync(ecosystemDir);
    const match = dirs.find(
      (d) =>
        d.toLowerCase() === project.toLowerCase() ||
        d.toLowerCase().includes(project.toLowerCase())
    );
    if (!match) return null;
    return getContract(match, contract);
  }

  if (contract) {
    const filePath = findFile(projectDir, contract);
    if (filePath) {
      return fs.readFileSync(filePath, "utf-8");
    }
    return null;
  }

  // Return overview if no specific contract requested
  const overviewPath = findFile(projectDir, `overview_${project}`);
  if (overviewPath) {
    return fs.readFileSync(overviewPath, "utf-8");
  }

  // Fallback: return first .md file
  const filePath = findFile(projectDir, "overview");
  if (filePath) {
    return fs.readFileSync(filePath, "utf-8");
  }

  return null;
}

export function listAvailableConcepts(): string[] {
  const conceptDir = path.join(CONTENT_DIR, "concepts");
  try {
    return fs
      .readdirSync(conceptDir)
      .filter((f) => f.endsWith(".md") && !f.startsWith("_"))
      .map((f) => f.replace(/\.md$/, ""));
  } catch {
    return [];
  }
}

export function listAvailablePatterns(): string[] {
  const patternDir = path.join(CONTENT_DIR, "patterns");
  try {
    return fs
      .readdirSync(patternDir)
      .filter((f) => f.endsWith(".md") && !f.startsWith("_"))
      .map((f) => f.replace(/\.md$/, ""));
  } catch {
    return [];
  }
}
