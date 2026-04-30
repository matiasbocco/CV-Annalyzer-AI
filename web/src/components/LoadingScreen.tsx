interface Props {
  text?: string
}

export default function LoadingScreen({
  text = 'Analizando CVs… puede tardar 15–30 segundos',
}: Props) {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center gap-4">
      <div className="w-10 h-10 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
      <p className="text-gray-600 animate-pulse">{text}</p>
    </div>
  )
}
