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

export function getCookbook(name: string): string | null {
  const cookbookDir = path.join(CONTENT_DIR, "cookbook");
  const filePath = findFile(cookbookDir, name);
  if (filePath) {
    return fs.readFileSync(filePath, "utf-8");
  }
  return null;
}

export function listAvailableCookbooks(): string[] {
  const cookbookDir = path.join(CONTENT_DIR, "cookbook");
  const results: string[] = [];
  try {
    for (const sub of fs.readdirSync(cookbookDir, { withFileTypes: true })) {
      if (sub.isDirectory()) {
        const subDir = path.join(cookbookDir, sub.name);
        for (const f of fs.readdirSync(subDir)) {
          if (f.endsWith(".md") && !f.startsWith("_")) {
            results.push(`${sub.name}/${f.replace(/\.md$/, "")}`);
          }
        }
      }
    }
  } catch {
    // directory doesn't exist
  }
  return results;
}

export function getEip(number: string): string | null {
  const eipDir = path.join(CONTENT_DIR, "reference", "eips");
  const padded = number.replace(/^eip-?0*/i, "").padStart(4, "0");
  const filePath = path.join(eipDir, `eip-${padded}.md`);
  if (fs.existsSync(filePath)) {
    return fs.readFileSync(filePath, "utf-8");
  }
  // fallback: fuzzy search
  const found = findFile(eipDir, `eip-${padded}`);
  if (found) {
    return fs.readFileSync(found, "utf-8");
  }
  return null;
}

export function listAvailableEips(): string[] {
  const eipDir = path.join(CONTENT_DIR, "reference", "eips");
  try {
    return fs
      .readdirSync(eipDir)
      .filter((f) => f.startsWith("eip-") && f.endsWith(".md"))
      .map((f) => f.replace(/\.md$/, ""))
      .sort();
  } catch {
    return [];
  }
}

export function getErgoscriptRef(name: string): string | null {
  const esDir = path.join(CONTENT_DIR, "reference", "ergoscript");
  const filePath = findFile(esDir, name);
  if (filePath) {
    return fs.readFileSync(filePath, "utf-8");
  }
  return null;
}

export function listAvailableErgoscriptRefs(): string[] {
  const esDir = path.join(CONTENT_DIR, "reference", "ergoscript");
  try {
    return fs
      .readdirSync(esDir)
      .filter((f) => f.endsWith(".md") && !f.startsWith("_") && !f.startsWith("overview"))
      .map((f) => f.replace(/\.md$/, ""));
  } catch {
    return [];
  }
}

export function getSkill(name: string): string | null {
  const skillDir = path.join(CONTENT_DIR, "skills");
  const filePath = findFile(skillDir, name);
  if (filePath) {
    return fs.readFileSync(filePath, "utf-8");
  }
  return null;
}

export function listAvailableSkills(): string[] {
  const skillDir = path.join(CONTENT_DIR, "skills");
  try {
    return fs
      .readdirSync(skillDir)
      .filter((f) => f.endsWith(".md") && !f.startsWith("_"))
      .map((f) => f.replace(/\.md$/, ""));
  } catch {
    return [];
  }
}

export function getAuditContext(): string {
  const esDir = path.join(CONTENT_DIR, "reference", "ergoscript");
  const parts: string[] = [];

  const knownIssuesPath = path.join(esDir, "known-issues.md");
  if (fs.existsSync(knownIssuesPath)) {
    parts.push(fs.readFileSync(knownIssuesPath, "utf-8"));
  }

  const auditContextPath = path.join(esDir, "audit-context.md");
  if (fs.existsSync(auditContextPath)) {
    parts.push(fs.readFileSync(auditContextPath, "utf-8"));
  }

  const methodologyPath = path.join(CONTENT_DIR, "patterns", "contract-audit-methodology.md");
  if (fs.existsSync(methodologyPath)) {
    parts.push(fs.readFileSync(methodologyPath, "utf-8"));
  }

  const auditProgramPath = path.join(esDir, "audit-program.md");
  if (fs.existsSync(auditProgramPath)) {
    parts.push(fs.readFileSync(auditProgramPath, "utf-8"));
  }

  return parts.join("\n\n---\n\n");
}
