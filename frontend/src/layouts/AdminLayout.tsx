import { NavLink, Outlet, useNavigate } from 'react-router-dom'

import logoMarkUrl from '../../../graphics/logo-128x128.png'
import { useSession } from '../context/SessionContext'

const navItems = [
  { to: '/admin', label: 'Dashboard', end: true },
  { to: '/admin/settings', label: 'Settings' },
  { to: '/admin/library', label: 'Library' },
  { to: '/admin/collections', label: 'Collections' },
  { to: '/admin/sources', label: 'Sources' },
  { to: '/admin/display-settings', label: 'Display' },
]

export function AdminLayout() {
  const { state, logout } = useSession()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="sidebar-brand-header">
            <img className="sidebar-brand-logo" src={logoMarkUrl} alt="SPF5000 logo" width={64} height={64} />
            <div className="sidebar-brand-copy">
              <p className="eyebrow">Super Picture Frame 5000</p>
              <h1>Admin Console</h1>
            </div>
          </div>
          <p className="sidebar-copy">Simple LAN management for the frame, sources, and slideshow.</p>
        </div>

        <nav className="sidebar-nav" aria-label="Primary navigation">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <a href="/display" className="button button--ghost sidebar-display-link">
            Open display surface
          </a>

          <div className="sidebar-session">
            <p className="sidebar-username">{state.user?.username ?? 'Admin session'}</p>
            <button type="button" className="button button--ghost sidebar-logout-btn" onClick={() => void handleLogout()}>
              Log out
            </button>
          </div>
        </div>
      </aside>

      <main className="content">
        <Outlet />
      </main>
    </div>
  )
}
