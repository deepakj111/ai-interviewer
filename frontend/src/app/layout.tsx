import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ai-interviewer | Privacy-First Multimodal Technical Interviewer",
  description:
    "Open-source, local-first technical interview preparation platform for Senior Data Scientists and Machine Learning Engineers targeting top product companies.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased selection:bg-blue-600 selection:text-white">
        {children}
      </body>
    </html>
  );
}
