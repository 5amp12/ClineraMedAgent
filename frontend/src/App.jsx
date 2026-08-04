import { BrowserRouter, Routes, Route } from 'react-router-dom'
import AppLayout from './layouts/AppLayout.jsx'
import Reports from './pages/Reports.jsx'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/reports/:id" element={<Reports />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
