export default function Home() {
  const mcpUrl = "https://ergo-knowledge-base.vercel.app/api/mcp";

  const preStyle = {
    background: "#0a0a0a",
    padding: "1rem",
    borderRadius: "4px",
    overflow: "auto" as const,
    fontSize: "0.85rem",
    border: "1px solid #1a3a1a",
    color: "#33ff33",
  };

  return (
    <main
      style={{
        maxWidth: "720px",
        margin: "0 auto",
        padding: "2rem",
        fontFamily: '"Courier New", Courier, monospace',
        lineHeight: 1.6,
        color: "#33ff33",
        background: "#000000",
        minHeight: "100vh",
      }}
    >
      <h1 style={{ color: "#00ff00", borderBottom: "1px solid #1a3a1a", paddingBottom: "0.5rem" }}>
        Ergo Developer Knowledge Base — MCP Server
      </h1>
      <p>
        An MCP (Model Context Protocol) server providing semantic search and
        documentation lookup across the Ergo blockchain developer knowledge
        base. 65 ecosystem projects, concept guides, contract analyses, and
        cross-cutting development patterns.
      </p>
      <p style={{ fontSize: "0.9rem", color: "#22aa22" }}>
        Works with any MCP-compatible client — Claude, Gemini, Codex, Cursor,
        VS Code, and more.
      </p>

      <h2 style={{ color: "#00ff00" }}>Setup</h2>

      <h3 style={{ color: "#00dd00" }}>Claude.ai (Web)</h3>
      <ol>
        <li>
          Go to{" "}
          <a href="https://claude.ai/customize/connectors" style={{ color: "#55ff55" }}>
            claude.ai/customize/connectors
          </a>
        </li>
        <li>
          Click <strong>+</strong> and set the URL to:{" "}
          <code style={{ color: "#00ff00", background: "#0a0a0a", padding: "2px 6px", borderRadius: "3px" }}>
            {mcpUrl}
          </code>
        </li>
        <li>
          Click through the auth prompt (no-op OAuth — public data, no real
          credentials needed)
        </li>
      </ol>

      <h3 style={{ color: "#00dd00" }}>Claude Code</h3>
      <p>
        Edit{" "}
        <code style={{ color: "#00ff00", background: "#0a0a0a", padding: "2px 6px", borderRadius: "3px" }}>
          ~/.claude/mcp.json
        </code>
        :
      </p>
      <pre style={preStyle}>
        {JSON.stringify(
          { mcpServers: { "ergo-code": { url: mcpUrl } } },
          null,
          2
        )}
      </pre>

      <h3 style={{ color: "#00dd00" }}>Gemini CLI (free)</h3>
      <p>
        Edit{" "}
        <code style={{ color: "#00ff00", background: "#0a0a0a", padding: "2px 6px", borderRadius: "3px" }}>
          ~/.gemini/settings.json
        </code>
        :
      </p>
      <pre style={preStyle}>
        {JSON.stringify(
          { mcpServers: { "ergo-code": { url: mcpUrl } } },
          null,
          2
        )}
      </pre>
      <p style={{ fontSize: "0.85rem", color: "#22aa22" }}>
        Free tier: 1,000 requests/day with a Google account.
      </p>

      <h3 style={{ color: "#00dd00" }}>OpenAI Codex CLI</h3>
      <p>
        Edit{" "}
        <code style={{ color: "#00ff00", background: "#0a0a0a", padding: "2px 6px", borderRadius: "3px" }}>
          ~/.codex/mcp.json
        </code>
        :
      </p>
      <pre style={preStyle}>
        {JSON.stringify(
          { mcpServers: { "ergo-code": { url: mcpUrl } } },
          null,
          2
        )}
      </pre>

      <h3 style={{ color: "#00dd00" }}>VS Code / Copilot</h3>
      <p>
        Add to{" "}
        <code style={{ color: "#00ff00", background: "#0a0a0a", padding: "2px 6px", borderRadius: "3px" }}>
          .vscode/mcp.json
        </code>{" "}
        in your workspace:
      </p>
      <pre style={preStyle}>
        {JSON.stringify(
          { servers: { "ergo-code": { url: mcpUrl } } },
          null,
          2
        )}
      </pre>

      <h3 style={{ color: "#00dd00" }}>Cursor</h3>
      <p>
        Go to <strong>Settings &gt; MCP</strong> and add the server URL:
      </p>
      <pre style={preStyle}>{mcpUrl}</pre>

      <h3 style={{ color: "#00dd00" }}>Windsurf</h3>
      <p>
        Edit{" "}
        <code style={{ color: "#00ff00", background: "#0a0a0a", padding: "2px 6px", borderRadius: "3px" }}>
          ~/.windsurf/mcp.json
        </code>
        :
      </p>
      <pre style={preStyle}>
        {JSON.stringify(
          { mcpServers: { "ergo-code": { url: mcpUrl } } },
          null,
          2
        )}
      </pre>

      <h3 style={{ color: "#00dd00" }}>Cline (free, open-source VS Code extension)</h3>
      <p>
        Open Cline settings and add a remote MCP server with URL:{" "}
        <code style={{ color: "#00ff00", background: "#0a0a0a", padding: "2px 6px", borderRadius: "3px" }}>
          {mcpUrl}
        </code>
      </p>

      <h2 style={{ color: "#00ff00" }}>Local Development</h2>
      <pre style={preStyle}>
        {`git clone https://github.com/cannonQ/ergo-knowledge-base.git
cd ergo-knowledge-base/mcp-server
cp .env.local.example .env.local
# Edit .env.local with your OpenAI API key
npm install && npm run dev`}
      </pre>

      <h2 style={{ color: "#00ff00" }}>Available Tools</h2>
      <table
        style={{
          width: "100%",
          borderCollapse: "collapse",
          marginTop: "0.5rem",
        }}
      >
        <thead>
          <tr style={{ borderBottom: "2px solid #1a3a1a", textAlign: "left" }}>
            <th style={{ padding: "0.5rem", color: "#00ff00" }}>Tool</th>
            <th style={{ padding: "0.5rem", color: "#00ff00" }}>Description</th>
          </tr>
        </thead>
        <tbody>
          {[
            ["search_docs", "Semantic vector search across all EKB content"],
            [
              "get_concept",
              "Retrieve concept docs (eUTXO, Sigma protocols, storage rent, etc.)",
            ],
            [
              "get_contract",
              "Get contract analysis for an ecosystem project",
            ],
            [
              "get_pattern",
              "Cross-cutting development pattern guides",
            ],
            [
              "get_cookbook",
              "Code recipes with ErgoScript + Fleet SDK (tokens, contracts)",
            ],
            [
              "get_eip",
              "Ergo Improvement Proposals by number (EIP-1 through EIP-44)",
            ],
            [
              "get_ergoscript_ref",
              "ErgoScript language reference (built-ins, types, context vars)",
            ],
            ["list_projects", "List all 65 ecosystem projects"],
            [
              "get_skill",
              "Complete skill docs: Nautilus, Babel fees, Fleet SDK, AVL, WASM, AppKit",
            ],
            [
              "audit_contract",
              "Pass 1: Initial ErgoScript security audit with full EKB context",
            ],
            [
              "audit_verify",
              "Pass 2: Independent verification of audit findings",
            ],
          ].map(([name, desc]) => (
            <tr key={name} style={{ borderBottom: "1px solid #1a3a1a" }}>
              <td style={{ padding: "0.5rem" }}>
                <strong style={{ color: "#00ff00" }}>{name}</strong>
              </td>
              <td style={{ padding: "0.5rem" }}>{desc}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <hr style={{ margin: "2rem 0", border: "none", borderTop: "1px solid #1a3a1a" }} />
      <p style={{ fontSize: "0.85rem", color: "#22aa22" }}>
        Source:{" "}
        <a href="https://github.com/cannonQ/ergo-knowledge-base" style={{ color: "#55ff55" }}>
          cannonQ/ergo-knowledge-base
        </a>{" "}
        · Licensed under{" "}
        <a href="https://www.gnu.org/licenses/agpl-3.0.html" style={{ color: "#55ff55" }}>
          AGPL-3.0
        </a>
      </p>
    </main>
  );
}
