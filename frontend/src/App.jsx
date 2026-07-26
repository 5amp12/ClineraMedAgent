import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import AppLayout from './layouts/AppLayout.jsx'
import Reports from './pages/Reports.jsx'
import Signin from './pages/Signin.jsx'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/signin" element={<Signin />} />
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/reports" replace />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="*" element={<Navigate to="/reports" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
