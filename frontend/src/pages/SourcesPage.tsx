import { useEffect, useState } from 'react'

import { getSources } from '../api/sources'

type Source = {
  id: string
  name: string
}

export function SourcesPage() {
  const [sources, setSources] = useState<Source[]>([])

  useEffect(() => {
    void getSources().then(setSources)
  }, [])

  return (
    <section>
      <h2>Sources</h2>
      <ul>
        {sources.map((source) => (
          <li key={source.id}>{source.name}</li>
        ))}
      </ul>
    </section>
  )
}
