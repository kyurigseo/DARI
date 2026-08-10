import { BrowserRouter, Route, Routes } from 'react-router-dom'
import AppLayout from './layouts/AppLayout'
import CardsPage from './pages/CardsPage'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import MeetingPage from './pages/MeetingPage'
import MyPage from './pages/MyPage'
import RehearsalPage from './pages/RehearsalPage'
import SignupPage from './pages/SignupPage'
import SummaryPage from './pages/SummaryPage'
import TrackerPage from './pages/TrackerPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />

        <Route element={<AppLayout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/rehearsal" element={<RehearsalPage />} />
          <Route path="/cards" element={<CardsPage />} />
          <Route path="/meeting/:meetingId" element={<MeetingPage />} />
          <Route path="/tracker" element={<TrackerPage />} />
          <Route path="/summary/:meetingId" element={<SummaryPage />} />
          <Route path="/mypage" element={<MyPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
