import { useQuery } from '@tanstack/react-query'
import client from './api/client'

export default function App() {
  const { isLoading, isError } = useQuery({
    queryKey: ['health'],
    queryFn: () => client.get('/').then((r) => r.data),
    retry: 1,
  })

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center p-10 bg-white rounded-2xl shadow-md space-y-3">
        <h1 className="text-2xl font-bold text-gray-800">CV Analyzer AI</h1>
        {isLoading && (
          <p className="text-lg text-gray-500">Loading…</p>
        )}
        {!isLoading && !isError && (
          <p className="text-lg font-semibold text-green-600">✓ Backend connected</p>
        )}
        {isError && (
          <p className="text-lg font-semibold text-red-600">✗ Backend not reachable</p>
        )}
      </div>
    </div>
  )
}
