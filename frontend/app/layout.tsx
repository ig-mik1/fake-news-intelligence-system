// frontend/app/layout.tsx
import { Plus_Jakarta_Sans } from "next/font/google";

import Background from "@/components/background";
import CommandPalette from "@/components/CommandPalette";
import Navbar from "@/components/Navbar";
import PageTransition from "@/components/PageTransition";
import "./globals.css";

const plusJakartaSans = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-plus-jakarta",
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body
        className={`${plusJakartaSans.variable} bg-slate-50 font-sans antialiased selection:bg-slate-200 selection:text-slate-900`}
      >
        <Background />
        <Navbar />
        <CommandPalette />
        <main className="relative z-10 min-h-screen pt-24">
          <PageTransition>
            {children}
          </PageTransition>
        </main>
      </body>
    </html>
  );
}
