import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import AppLayout from './layouts/AppLayout.jsx'
import Reports from './pages/Reports.jsx'
import ReportsIndex from './pages/ReportsIndex.jsx'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          {/* /reports is the landing page. It used to be undefined, so the sidebar's only nav
              link rendered a blank page — AppLayout is a layout route, so an unmatched child
              took the sidebar down with it and left no way back except editing the URL. */}
          <Route path="/reports" element={<ReportsIndex />} />
          <Route path="/reports/:id" element={<Reports />} />
          <Route path="*" element={<Navigate to="/reports" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
