import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import AppLayout from './layouts/AppLayout.jsx'
import Reports from './pages/Reports.jsx'
import Placeholder from './pages/Placeholder.jsx'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/reports" replace />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/add-people" element={<Placeholder title="Add People" />} />
          <Route path="/ask-clinera" element={<Placeholder title="Ask Clinera" />} />
          <Route path="/folders" element={<Placeholder title="Folders" />} />
          <Route path="/calendar" element={<Placeholder title="Calendar" />} />
          <Route path="/integrations" element={<Placeholder title="Integrations" />} />
          <Route path="/for-you" element={<Placeholder title="For You" />} />
          <Route path="/coaching" element={<Placeholder title="Coaching" />} />
          <Route path="/recommendations" element={<Placeholder title="Recommendations" />} />
          <Route path="/meeting-policy" element={<Placeholder title="Meeting Policy" />} />
          <Route path="*" element={<Navigate to="/reports" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
