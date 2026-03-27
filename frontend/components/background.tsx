export default function Background() {
  return (
    <div className="fixed inset-0 -z-10 overflow-hidden bg-slate-50">
      <div className="absolute inset-x-0 top-0 h-[520px] bg-[radial-gradient(circle_at_top_left,_rgba(191,219,254,0.55),_transparent_40%),radial-gradient(circle_at_top_right,_rgba(226,232,240,0.9),_transparent_35%),linear-gradient(180deg,_rgba(255,255,255,0.96)_0%,_rgba(248,250,252,1)_100%)]" />
      <div className="absolute left-[-8%] top-16 h-[28rem] w-[28rem] rounded-full bg-sky-100/70 blur-[96px] animate-blob" />
      <div className="absolute right-[-10%] top-24 h-[34rem] w-[34rem] rounded-full bg-cyan-100/70 blur-[120px] animate-blob animation-delay-2000" />
      <div className="absolute bottom-[-12%] left-[30%] h-[24rem] w-[24rem] rounded-full bg-emerald-100/40 blur-[120px] animate-blob animation-delay-4000" />
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0)_0%,rgba(255,255,255,0.75)_70%,rgba(248,250,252,1)_100%)]" />
    </div>
  );
}
