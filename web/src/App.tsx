import { BrowserRouter, Routes, Route } from 'react-router-dom'
import NavBar from './components/NavBar'
import ProtectedRoute from './components/ProtectedRoute'
import AdminRoute from './components/AdminRoute'
import AnalyzePage from './pages/AnalyzePage'
import MatchPage from './pages/MatchPage'
import UploadPage from './pages/UploadPage'
import LoginPage from './pages/LoginPage'
import ChangePasswordPage from './pages/ChangePasswordPage'
import AdminPage from './pages/AdminPage'
import HistoryPage from './pages/HistoryPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes — no NavBar, no auth check */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/upload" element={<><NavBar /><UploadPage /></>} />

        {/* Protected routes — redirect to /login if not authenticated */}
        <Route element={<ProtectedRoute />}>
          <Route path="/change-password" element={<><NavBar /><ChangePasswordPage /></>} />
          <Route path="/" element={<><NavBar /><AnalyzePage /></>} />
          <Route path="/match" element={<><NavBar /><MatchPage /></>} />
          <Route path="/history" element={<><NavBar /><HistoryPage /></>} />
        </Route>

        {/* Admin-only routes — redirect recruiters to / */}
        <Route element={<AdminRoute />}>
          <Route path="/admin" element={<><NavBar /><AdminPage /></>} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
