export default function Home() {
  return (
    <main style={{ padding: "2rem", fontFamily: "monospace" }}>
      <h1>Ergo Developer Knowledge Base — MCP Server</h1>
      <p>
        This is an MCP (Model Context Protocol) server for the Ergo blockchain
        developer knowledge base.
      </p>
      <h2>Connect</h2>
      <p>Add this to your MCP client configuration:</p>
      <pre
        style={{
          background: "#f4f4f4",
          padding: "1rem",
          borderRadius: "4px",
        }}
      >
        {JSON.stringify(
          {
            mcpServers: {
              ergo: {
                url: "https://ergo-ekb.vercel.app/api/mcp",
              },
            },
          },
          null,
          2
        )}
      </pre>
      <h2>Available Tools</h2>
      <ul>
        <li>
          <strong>search_docs</strong> — Semantic search across all EKB content
        </li>
        <li>
          <strong>get_concept</strong> — Retrieve concept docs (eUTXO, Sigma
          protocols, etc.)
        </li>
        <li>
          <strong>get_contract</strong> — Get contract analysis for ecosystem
          projects
        </li>
        <li>
          <strong>get_pattern</strong> — Cross-cutting development pattern
          guides
        </li>
        <li>
          <strong>list_projects</strong> — List all 55 ecosystem projects
        </li>
      </ul>
    </main>
  );
}
