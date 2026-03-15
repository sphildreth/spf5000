import { NavLink, Outlet } from 'react-router-dom'

const navItems = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/settings', label: 'Settings' },
  { to: '/library', label: 'Library' },
  { to: '/collections', label: 'Collections' },
  { to: '/sources', label: 'Sources' },
  { to: '/display-settings', label: 'Display' },
]

export function AdminLayout() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <p className="eyebrow">Super Picture Frame 5000</p>
          <h1>Admin Console</h1>
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
        </div>
      </aside>

      <main className="content">
        <Outlet />
      </main>
    </div>
  )
}
