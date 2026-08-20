import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getDashboard } from '../../api/home'
import CreateMeetingModal from './CreateMeetingModal'
import './HomePage.css'

function formatTime(isoString) {
  if (!isoString) return ''
  const date = new Date(isoString)
  return date.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', hour12: false })
}

function buildQuickLinks(quickStats) {
  if (!quickStats) return []

  const links = []

  links.push({
    icon: '🗂️',
    title: `발언 카드 ${quickStats.speech_card?.count ?? 0}개`,
    description: '저장한 실전 문장 모아보기',
    to: '/cards',
  })

  if (quickStats.tracker_alert?.has_alert) {
    links.push({
      icon: '🌓',
      title: '시차 형평성',
      description: quickStats.tracker_alert.message,
      to: '/tracker',
      tone: 'warning',
    })
  }

  if (quickStats.latest_summary?.available) {
    links.push({
      icon: '📝',
      title: '최근 회의 요약',
      description: `${quickStats.latest_summary.meeting_title} · Action Item ${quickStats.latest_summary.action_item_count}건`,
      to: '/summary',
    })
  }

  if (quickStats.rehearsal_continue?.available) {
    links.push({
      icon: '🎭',
      title: 'AI 리허설 이어하기',
      description: `${quickStats.rehearsal_continue.persona_name}님과 마지막 대화`,
      to: '/rehearsal',
    })
  }

  return links
}

function HomePage() {
  const [dashboard, setDashboard] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)

  useEffect(() => {
    let isMounted = true

    getDashboard()
      .then((data) => {
        if (isMounted) setDashboard(data)
      })
      .catch(() => {
        if (isMounted) setError('대시보드 정보를 불러오지 못했습니다.')
      })
      .finally(() => {
        if (isMounted) setIsLoading(false)
      })

    return () => {
      isMounted = false
    }
  }, [])

  if (isLoading) {
    return (
      <div className="home-page">
        <p>불러오는 중...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="home-page">
        <p>{error}</p>
      </div>
    )
  }

  const meetings = dashboard?.today_meetings ?? []
  const quickLinks = buildQuickLinks(dashboard?.quick_stats)

  return (
    <div className="home-page">
      <div className="home-page__heading-row">
        <div className="home-page__heading">
          <h1>{dashboard?.greeting ?? '안녕하세요 👋'}</h1>
          <p>오늘 {dashboard?.today_meeting_count ?? meetings.length}개의 회의가 예정되어 있어요</p>
        </div>
        <button
          type="button"
          className="home-page__create-button"
          onClick={() => setIsCreateModalOpen(true)}
        >
          <span aria-hidden="true">＋</span> 새 회의 만들기
        </button>
      </div>

      <section className="home-page__meetings" aria-label="오늘의 회의">
        {meetings.length === 0 && <p>오늘 예정된 회의가 없어요.</p>}
        {meetings.map((meeting, index) => (
          <article
            className={`meeting-card${index === 0 ? ' meeting-card--next' : ''}`}
            key={meeting.meeting_id}
          >
            <time className="meeting-card__time">{formatTime(meeting.start_time)}</time>
            <div className="meeting-card__content">
              <div className="meeting-card__title-row">
                <h2>{meeting.title}</h2>
                {index === 0 && <span className="meeting-card__badge">다음 회의</span>}
              </div>
              <p>{meeting.participant_count}명 참석 예정</p>
            </div>
            <Link
              className="meeting-card__button"
              to={meeting.join_url || `/meeting/${meeting.room_code || meeting.meeting_id}`}
            >
              참가하기 <span aria-hidden="true">→</span>
            </Link>
          </article>
        ))}
      </section>

      <section className="home-page__quick-links" aria-label="빠른 메뉴">
        {quickLinks.map((item) => (
          <Link className="quick-link-card" to={item.to} key={item.title}>
            <div>
              <span className="quick-link-card__icon" aria-hidden="true">
                {item.icon}
              </span>
              <h2>{item.title}</h2>
            </div>
            <p className={item.tone === 'warning' ? 'quick-link-card__warning' : ''}>
              {item.tone === 'warning' && <span aria-hidden="true">⚠ </span>}
              {item.description}
            </p>
          </Link>
        ))}
      </section>

      {isCreateModalOpen && (
        <CreateMeetingModal onClose={() => setIsCreateModalOpen(false)} />
      )}
    </div>
  )
}

export default HomePage
