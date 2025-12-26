interface KBSuggestion {
  id: string
  title: string
  url: string
  snippet: string
}

interface KBSuggestionsProps {
  suggestions: KBSuggestion[]
  onSelect: (suggestion: KBSuggestion) => void
}

export function KBSuggestions({ suggestions, onSelect }: KBSuggestionsProps) {
  if (suggestions.length === 0) return null

  return (
    <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
      {suggestions.map((suggestion) => (
        <button
          key={suggestion.id}
          onClick={() => onSelect(suggestion)}
          className="text-left p-4 bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md hover:border-[#0A2540] transition-all"
        >
          <h3 className="font-semibold text-[#0A2540] mb-2">{suggestion.title}</h3>
          <p className="text-sm text-gray-600 line-clamp-2">{suggestion.snippet}</p>
        </button>
      ))}
    </div>
  )
}

