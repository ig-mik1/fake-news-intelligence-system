// frontend/app/page.tsx
"use client";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();

  return (
    <div className="relative min-h-[90vh] flex flex-col items-center justify-center">
      <motion.div 
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center z-10 px-6"
      >
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-blue-100 bg-blue-50/50 text-blue-700 text-xs font-semibold mb-8">
          <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse" />
          AI News Intelligence Platform
        </div>

        <h1 className="text-7xl font-extrabold tracking-tight text-slate-900 mb-6 leading-[1.1]">
          Verify News with <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 via-indigo-600 to-blue-500">
            Absolute Confidence
          </span>
        </h1>

        <p className="text-slate-500 text-lg max-w-2xl mx-auto mb-12 font-medium">
          Our AI News Intelligence platform uses cross-consensus checking and trust scoring 
          to identify misinformation in real-time.
        </p>

        <button 
          onClick={() => router.push("/verify")}
          className="bg-[#0f172a] text-white px-10 py-4 rounded-xl font-bold text-lg hover:bg-black transition-all shadow-2xl shadow-blue-900/20 active:scale-95"
        >
          Start Verification
        </button>
      </motion.div>
    </div>
  );
}
