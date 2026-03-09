export default function Home() {
  const mcpUrl = "https://ergo-knowledge-base.vercel.app/api/mcp";

  return (
    <main
      style={{
        maxWidth: "720px",
        margin: "0 auto",
        padding: "2rem",
        fontFamily:
          '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace',
        lineHeight: 1.6,
        color: "#1a1a1a",
      }}
    >
      <h1>Ergo Developer Knowledge Base — MCP Server</h1>
      <p>
        An MCP (Model Context Protocol) server providing semantic search and
        documentation lookup across the Ergo blockchain developer knowledge
        base. 61 ecosystem projects, concept guides, contract analyses, and
        cross-cutting development patterns.
      </p>

      <h2>Claude.ai (Web)</h2>
      <ol>
        <li>
          Go to{" "}
          <a href="https://claude.ai/customize/connectors">
            claude.ai/customize/connectors
          </a>
        </li>
        <li>
          Click <strong>+</strong> to add a custom connector
        </li>
        <li>
          Set the URL to: <code>{mcpUrl}</code>
        </li>
        <li>
          When prompted to authenticate, just click through — the server uses a{" "}
          <strong>no-op OAuth flow</strong> (public data, no real credentials
          needed)
        </li>
        <li>
          Once connected, Claude will have access to the EKB tools in any
          conversation
        </li>
      </ol>

      <h2>Claude Code (CLI)</h2>
      <p>
        Create or edit <code>~/.claude/mcp.json</code>:
      </p>
      <pre
        style={{
          background: "#f4f4f4",
          padding: "1rem",
          borderRadius: "4px",
          overflow: "auto",
        }}
      >
        {JSON.stringify(
          { mcpServers: { "ergo-code": { url: mcpUrl } } },
          null,
          2
        )}
      </pre>
      <p>Then restart Claude Code (close the chat window and open a new one).</p>

      <h2>Local Development</h2>
      <pre
        style={{
          background: "#f4f4f4",
          padding: "1rem",
          borderRadius: "4px",
          overflow: "auto",
        }}
      >
        {`git clone https://github.com/cannonQ/ergo-knowledge-base.git
cd ergo-knowledge-base/mcp-server
cp .env.local.example .env.local
# Edit .env.local with your OpenAI API key
npm install && npm run dev`}
      </pre>

      <h2>Available Tools</h2>
      <table
        style={{
          width: "100%",
          borderCollapse: "collapse",
          marginTop: "0.5rem",
        }}
      >
        <thead>
          <tr style={{ borderBottom: "2px solid #ddd", textAlign: "left" }}>
            <th style={{ padding: "0.5rem" }}>Tool</th>
            <th style={{ padding: "0.5rem" }}>Description</th>
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
            ["list_projects", "List all 55 ecosystem projects"],
          ].map(([name, desc]) => (
            <tr key={name} style={{ borderBottom: "1px solid #eee" }}>
              <td style={{ padding: "0.5rem" }}>
                <strong>{name}</strong>
              </td>
              <td style={{ padding: "0.5rem" }}>{desc}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <hr style={{ margin: "2rem 0", border: "none", borderTop: "1px solid #ddd" }} />
      <p style={{ fontSize: "0.85rem", color: "#666" }}>
        Source:{" "}
        <a href="https://github.com/cannonQ/ergo-knowledge-base">
          cannonQ/ergo-knowledge-base
        </a>{" "}
        · Licensed under{" "}
        <a href="https://www.gnu.org/licenses/agpl-3.0.html">AGPL-3.0</a>
      </p>
    </main>
  );
}
