import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MainAgent",
  description: "PocketFlow-powered research assistant"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

