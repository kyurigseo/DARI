import { Outlet } from 'react-router-dom'

function AppLayout() {
  return (
    <div className="app-layout">
      <header className="app-header">DARI</header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  )
}

export default AppLayout
