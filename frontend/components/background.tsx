// frontend/components/background.tsx
import React from 'react'

export default function Background() {
  return (
    <div className="fixed inset-0 -z-10 h-full w-full bg-white overflow-hidden">
      {/* Soft Top-Left Blob */}
      <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-blue-100/50 rounded-full mix-blend-multiply filter blur-[80px] opacity-70 animate-blob" />
      
      {/* Soft Bottom-Right Blob (Delayed) [cite: 7, 12] */}
      <div className="absolute bottom-[-10%] right-[-10%] w-[600px] h-[600px] bg-indigo-100/40 rounded-full mix-blend-multiply filter blur-[100px] opacity-60 animate-blob animation-delay-2000" />
      
      {/* Subtle Center Blob */}
      <div className="absolute top-[20%] right-[10%] w-[400px] h-[400px] bg-purple-50/50 rounded-full mix-blend-multiply filter blur-[120px] opacity-50 animate-blob animation-delay-4000" />
    </div>
  )
}