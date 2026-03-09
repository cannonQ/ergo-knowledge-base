export const metadata = {
  title: "Ergo EKB MCP Server",
  description: "MCP server for the Ergo Developer Knowledge Base",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body style={{ margin: 0, background: "#000000" }}>{children}</body>
    </html>
  );
}
