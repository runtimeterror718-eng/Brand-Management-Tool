import React from 'react'
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import BrandView from './pages/BrandView'
import Search from './pages/Search'
import Alerts from './pages/Alerts'

function Nav() {
  const link = (to, label) => (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
          isActive
            ? 'bg-indigo-600 text-white'
            : 'text-gray-600 hover:bg-gray-100'
        }`
      }
    >
      {label}
    </NavLink>
  )

  return (
    <nav className="bg-white border-b px-6 py-3 flex items-center gap-2">
      <span className="font-bold text-lg mr-6">Brand Tool</span>
      {link('/', 'Dashboard')}
      {link('/search', 'Search')}
      {link('/alerts', 'Alerts')}
    </nav>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Nav />
      <main className="p-6 max-w-7xl mx-auto">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/brand/:brandId" element={<BrandView />} />
          <Route path="/search" element={<Search />} />
          <Route path="/alerts" element={<Alerts />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}
