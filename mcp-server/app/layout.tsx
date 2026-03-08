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
      <body>{children}</body>
    </html>
  );
}
