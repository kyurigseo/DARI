import { BrowserRouter, Route, Routes } from 'react-router-dom'
import AppLayout from './layouts/AppLayout'
import ProtectedRoute from './components/common/ProtectedRoute'
import LoginPage from './pages/auth/LoginPage'
import SignupPage from './pages/auth/SignupPage'
import CardsPage from './pages/cards/CardsPage'
import HomePage from './pages/home/HomePage'
import MeetingPage from './pages/meeting/MeetingPage'
import MyPage from './pages/mypage/MyPage'
import RehearsalPage from './pages/rehearsal/RehearsalPage'
import SummaryPage from './pages/summary/SummaryPage'
import TrackerPage from './pages/tracker/TrackerPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />

        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/rehearsal" element={<RehearsalPage />} />
            <Route path="/cards" element={<CardsPage />} />
            <Route path="/meeting/:meetingId" element={<MeetingPage />} />
            <Route path="/tracker" element={<TrackerPage />} />
            <Route path="/summary/:meetingId" element={<SummaryPage />} />
            <Route path="/mypage" element={<MyPage />} />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
