import { NavLink, Outlet } from 'react-router-dom'

export function AdminLayout() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h1>SPF5000</h1>
        <nav>
          <NavLink to="/">Dashboard</NavLink>
          <NavLink to="/settings">Settings</NavLink>
          <NavLink to="/sources">Sources</NavLink>
          <NavLink to="/display">Display</NavLink>
        </nav>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  )
}
