import { useCategories } from './api/hooks'

export default function App() {
  const { data: categories, isLoading, isError } = useCategories()

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="p-10 bg-white rounded-2xl shadow-md w-full max-w-sm space-y-4">
        <h1 className="text-2xl font-bold text-gray-800">CV Analyzer AI</h1>

        {isLoading && (
          <p className="text-gray-500">Loading categories…</p>
        )}

        {isError && (
          <p className="font-semibold text-red-600">✗ Backend not reachable</p>
        )}

        {categories && (
          <>
            <p className="text-sm text-green-600 font-semibold">✓ Backend connected</p>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-2">
                Job categories ({categories.length})
              </p>
              {categories.length === 0 ? (
                <p className="text-sm text-gray-400">No categories yet — run an analysis first.</p>
              ) : (
                <ul className="space-y-1">
                  {categories.map((cat) => (
                    <li key={cat.slug} className="text-sm text-gray-700">
                      {cat.display_name}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
