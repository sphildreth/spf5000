import { Navigate, Route, Routes } from 'react-router-dom'

import { AdminLayout } from './layouts/AdminLayout'
import { CollectionsPage } from './pages/CollectionsPage'
import { DashboardPage } from './pages/DashboardPage'
import { DisplayPage } from './pages/DisplayPage'
import { DisplaySettingsPage } from './pages/DisplaySettingsPage'
import { LibraryPage } from './pages/LibraryPage'
import { SettingsPage } from './pages/SettingsPage'
import { SourcesPage } from './pages/SourcesPage'

export default function App() {
  return (
    <Routes>
      <Route path="/display" element={<DisplayPage />} />
      <Route element={<AdminLayout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/library" element={<LibraryPage />} />
        <Route path="/collections" element={<CollectionsPage />} />
        <Route path="/sources" element={<SourcesPage />} />
        <Route path="/display-settings" element={<DisplaySettingsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
