interface Props {
  message?: string
}

export default function LoadingOverlay({ message = 'Analyzing repository…' }: Props) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-7 py-24 animate-fade-in relative z-10">
      {/* Multi-orbit animated spinner with ambient glow */}
      <div className="relative w-24 h-24 flex items-center justify-center">
        {/* Ambient radial blur aura */}
        <div className="absolute inset-0 rounded-full bg-blue-500/20 blur-xl animate-pulse-glow" />

        <div className="absolute inset-0 rounded-full border-[3px] border-white/[0.06] shadow-inner" />
        <div className="absolute inset-0 rounded-full border-[3px] border-transparent
                        border-t-blue-500 border-r-indigo-500/40 animate-spin drop-shadow-[0_0_15px_rgba(59,130,246,0.8)]" />
        <div className="absolute inset-3 rounded-full border-[3px] border-transparent
                        border-t-cyan-400 border-l-blue-400/40 animate-spin [animation-duration:1.1s] [animation-direction:reverse]" />
        <div className="absolute inset-6 rounded-full border-2 border-transparent border-t-purple-400 animate-spin [animation-duration:1.8s]" />
        
        <div className="w-4 h-4 rounded-full bg-gradient-to-tr from-blue-500 to-cyan-400 animate-pulse shadow-[0_0_12px_rgba(59,130,246,0.9)]" />
      </div>

      <div className="text-center space-y-1.5">
        <p className="text-lg font-bold text-white tracking-tight">{message}</p>
        <p className="text-sm text-gray-400 max-w-sm mx-auto leading-relaxed">
          Cloning repository, scanning files, building embeddings…
        </p>
      </div>

      {/* Progress hints container with glass styling */}
      <div className="flex flex-col gap-3 mt-2 bg-gray-900/70 border border-white/[0.08] rounded-2xl px-6 py-4.5 shadow-xl shadow-black/30 backdrop-blur-md">
        {['Cloning repository', 'Scanning files', 'Detecting languages & frameworks', 'Building search index'].map((step, idx) => (
          <div key={step} className="flex items-center gap-3 text-xs text-gray-400">
            <span
              className="inline-block w-2 h-2 rounded-full bg-blue-400 animate-pulse shadow-[0_0_8px_rgba(96,165,250,0.9)]"
              style={{ animationDelay: `${idx * 250}ms` }}
            />
            <span className="font-medium text-gray-300">{step}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
