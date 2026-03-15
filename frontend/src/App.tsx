import { Route, Routes } from 'react-router-dom'

import { AdminLayout } from './layouts/AdminLayout'
import { DisplayPage } from './pages/DisplayPage'
import { DashboardPage } from './pages/DashboardPage'
import { SettingsPage } from './pages/SettingsPage'
import { SourcesPage } from './pages/SourcesPage'

export default function App() {
  return (
    <Routes>
      <Route path="/display" element={<DisplayPage />} />
      <Route element={<AdminLayout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/sources" element={<SourcesPage />} />
      </Route>
    </Routes>
  )
}
