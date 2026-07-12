import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Relay Bench — Context Compression Study",
  description: "A controlled A/B benchmark for agent context compression.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
