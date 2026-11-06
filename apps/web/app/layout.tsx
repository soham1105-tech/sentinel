import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SENTINEL — The Agent That Tests Agents",
  description:
    "The supervisor agent that tests, breaks, and fixes other AI agents before they ship.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-ink text-white antialiased">{children}</body>
    </html>
  );
}
