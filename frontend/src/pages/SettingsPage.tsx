import { useEffect, useState } from 'react'

import { getSettings } from '../api/settings'

type Settings = {
  slideshow_interval_seconds: number
  transition_mode: string
  fit_mode: string
  shuffle_enabled: boolean
}

export function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null)

  useEffect(() => {
    void getSettings().then(setSettings)
  }, [])

  return (
    <section>
      <h2>Settings</h2>
      {settings ? <pre>{JSON.stringify(settings, null, 2)}</pre> : <p>Loading...</p>}
    </section>
  )
}
