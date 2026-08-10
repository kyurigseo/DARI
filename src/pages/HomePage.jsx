import { Link } from 'react-router-dom'
import './HomePage.css'

const meetings = [
  {
    id: 'm1',
    time: '14:00',
    title: 'Acme Corp 협상',
    attendees: 4,
  },
  {
    id: 'm2',
    time: '16:30',
    title: '주간 팀 스탠드업',
    attendees: 6,
  },
  {
    id: 'm3',
    time: '19:00',
    title: '베를린 지사 동기화',
    attendees: 3,
  },
]

const quickLinks = [
  {
    icon: '🗂️',
    title: '발언 카드 2개',
    description: '저장한 실전 문장 모아보기',
    to: '/cards',
  },
  {
    icon: '🌓',
    title: '시차 형평성',
    description: '지민님 이번 달 5/6 새벽 참여',
    to: '/tracker',
    tone: 'warning',
  },
  {
    icon: '📝',
    title: '최근 회의 요약',
    description: 'Q3 예산안 협상 · Action Item 2건',
    to: '/summary/m1',
  },
  {
    icon: '🎭',
    title: 'AI 리허설 이어하기',
    description: '🇩🇪 독일 팀장님과 마지막 대화',
    to: '/rehearsal',
  },
]

function HomePage() {
  return (
    <div className="home-page">
      <div className="home-page__heading">
        <h1>안녕하세요 👋</h1>
        <p>오늘 {meetings.length}개의 회의가 예정되어 있어요</p>
      </div>

      <section className="home-page__meetings" aria-label="오늘의 회의">
        {meetings.map((meeting, index) => (
          <article
            className={`meeting-card${index === 0 ? ' meeting-card--next' : ''}`}
            key={meeting.id}
          >
            <time className="meeting-card__time">{meeting.time}</time>
            <div className="meeting-card__content">
              <div className="meeting-card__title-row">
                <h2>{meeting.title}</h2>
                {index === 0 && <span className="meeting-card__badge">다음 회의</span>}
              </div>
              <p>{meeting.attendees}명 참석 예정</p>
            </div>
            <Link className="meeting-card__button" to={`/meeting/${meeting.id}`}>
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
    </div>
  )
}

export default HomePage
