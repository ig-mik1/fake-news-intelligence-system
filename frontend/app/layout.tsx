// frontend/app/layout.tsx
import Background from "@/components/background";
import Navbar from "@/components/Navbar";
import PageTransition from "@/components/PageTransition";
import "./globals.css";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased selection:bg-blue-100">
        <Background />
        <Navbar />
        <main className="relative z-10 pt-20">
          <PageTransition>
            {children}
          </PageTransition>
        </main>
      </body>
    </html>
  );
}
