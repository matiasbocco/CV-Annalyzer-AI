interface Props {
  text?: string
}

export default function LoadingScreen({
  text = 'Procesando…',
}: Props) {
  return (
    <div className="min-h-screen bg-[#0A0A0F] flex flex-col items-center justify-center gap-4">
      <div className="w-10 h-10 rounded-full border-2 border-slate-700 border-t-sky-500 animate-spin" />
      <p className="text-slate-400 text-sm animate-pulse">{text}</p>
    </div>
  )
}
