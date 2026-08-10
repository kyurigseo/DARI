import { useEffect, useRef, useState } from 'react'
import {
  availabilityStatusLabels,
  initialAvailability,
  localTimes,
  recentParticipants,
  timeLabels,
} from './trackerMockData'
import './TrackerPage.css'

const statusOrder = ['comfortable', 'normal', 'uncomfortable']

function TrackerPage() {
  const [finderExpanded, setFinderExpanded] = useState(false)
  const [availability, setAvailability] = useState(initialAvailability)
  const [selectedRecommendedTime] = useState('13:00')
  const [modalOpen, setModalOpen] = useState(false)
  const [meetingTitle, setMeetingTitle] = useState('시차 조율 회의')
  const [confirmed, setConfirmed] = useState(false)
  const [toast, setToast] = useState('')
  const toastTimerRef = useRef(null)

  const cycleMyAvailability = (cellIndex) => {
    setAvailability((currentAvailability) => {
      const currentStatus = currentAvailability.me[cellIndex]
      const nextStatus = statusOrder[(statusOrder.indexOf(currentStatus) + 1) % statusOrder.length]

      return {
        ...currentAvailability,
        me: currentAvailability.me.map((status, index) => (index === cellIndex ? nextStatus : status)),
      }
    })
  }

  const showToast = (message) => {
    setToast(message)

    if (toastTimerRef.current) {
      clearTimeout(toastTimerRef.current)
    }

    toastTimerRef.current = setTimeout(() => setToast(''), 2500)
  }

  const confirmMeeting = () => {
    setConfirmed(true)
    setModalOpen(false)
    showToast('13:00 회의를 확정하고 홈에 추가했어요 ✅')

    // TODO: 일정 확정 API가 준비되면 회의 제목과 추천 시간을 서버에 저장합니다.
    // TODO: 공통 일정 상태가 마련되면 Header의 다음 회의 정보도 갱신합니다.
  }

  useEffect(() => {
    if (!modalOpen) return undefined

    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') setModalOpen(false)
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [modalOpen])

  useEffect(
    () => () => {
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current)
    },
    [],
  )

  return (
    <section className="tracker-page">
      <header className="tracker-page__heading">
        <h1>시차 형평성 트래커</h1>
        <p>참여 시간대 기록을 보고, 모두에게 공정한 회의 시간을 함께 찾아보세요</p>
      </header>

      <section className="participation-card" aria-labelledby="participation-title">
        <h2 id="participation-title">최근 6회 참여 시간대</h2>
        <div className="participation-card__list">
          {recentParticipants.map((participant) => (
            <div className={`participation-row participation-row--${participant.tone}`} key={participant.name}>
              <span className="participation-row__avatar">{participant.name}</span>
              <div className="participation-row__track" aria-hidden="true">
                <span style={{ width: `${participant.percent}%` }} />
              </div>
              <span className="participation-row__badge">{participant.badge}</span>
            </div>
          ))}
        </div>
      </section>

      <div className="tracker-warning">
        <span aria-hidden="true">⚠️</span>
        <span>지민님이 이번 달 6번 중 5번, 새벽 시간대(03~06시)에 참여했어요.</span>
      </div>

      <section className={`time-finder${finderExpanded ? ' time-finder--expanded' : ''}`}>
        <header className="time-finder__header">
          <div>
            <h2>🗓️ 모두의 시간 찾기</h2>
            <p>30분 단위로 다같이 가능한 시간을 찾아요</p>
          </div>
          <button type="button" onClick={() => setFinderExpanded((expanded) => !expanded)}>
            {finderExpanded ? '접기 ▲' : '펼치기 ▼'}
          </button>
        </header>

        {finderExpanded && (
          <div className="time-finder__content">
            <div className="availability-legend">
              <div>
                <span className="legend-item legend-item--comfortable">● 편한 시간</span>
                <span className="legend-item legend-item--normal">● 보통</span>
                <span className="legend-item legend-item--uncomfortable">● 불편한 시간</span>
              </div>
              <strong>🔵 내 행 (클릭해서 조정)</strong>
            </div>

            <div className="availability-scroll">
              <div className="availability-grid">
                <div className="availability-grid__times" aria-hidden="true">
                  <span />
                  {timeLabels.map((time) => (
                    <span key={time}>{time}</span>
                  ))}
                </div>

                {Object.entries(availability).map(([participantId, statuses]) => (
                  <div
                    className={`availability-row${participantId === 'me' ? ' availability-row--me' : ''}`}
                    key={participantId}
                  >
                    <strong>{localTimes.find((person) => person.id === participantId).name}</strong>
                    <div className="availability-row__cells">
                      {statuses.map((status, index) => {
                        const time = `${String(Math.floor(index / 2)).padStart(2, '0')}:${index % 2 ? '30' : '00'}`

                        return participantId === 'me' ? (
                          <button
                            className={`availability-cell availability-cell--${status}`}
                            type="button"
                            aria-label={`나 ${time}, ${availabilityStatusLabels[status]}. 클릭해서 변경`}
                            onClick={() => cycleMyAvailability(index)}
                            key={time}
                          />
                        ) : (
                          <span
                            className={`availability-cell availability-cell--${status}`}
                            title={`${time} ${availabilityStatusLabels[status]}`}
                            key={time}
                          />
                        )
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="recommendation-panel">
              <h3>
                {confirmed ? '🔒 확정된 회의 시간' : '🏆 추천 시간대'} — {selectedRecommendedTime} (KST)
              </h3>
              <p className="recommendation-panel__warning">🔴 일부 참석자에게 불편한 시간이에요</p>
              <div className="recommendation-panel__people">
                {localTimes.map((person) => (
                  <div key={person.id}>
                    <span><strong>{person.name}</strong> · 현지 {person.time}</span>
                    <span className={`recommendation-status recommendation-status--${person.status}`}>
                      ● {person.status === 'comfortable' ? '✅ 편한 시간' : '🔴 불편한 시간'}
                    </span>
                  </div>
                ))}
              </div>
              <button
                className={`recommendation-panel__button${confirmed ? ' recommendation-panel__button--adjust' : ''}`}
                type="button"
                onClick={() => (confirmed ? setConfirmed(false) : setModalOpen(true))}
              >
                {confirmed ? '다시 조정하기' : '이 시간으로 일정 확정하기'}
              </button>
              {/* TODO: 공통 회의 시간 추천 API가 준비되면 13:00 Mock 결과를 교체합니다. */}
            </div>
          </div>
        )}
      </section>

      {modalOpen && (
        <div className="tracker-modal-backdrop" onMouseDown={() => setModalOpen(false)}>
          <section
            className="tracker-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="tracker-modal-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <h2 id="tracker-modal-title">회의 일정 확정</h2>
            <p>{selectedRecommendedTime} (KST)에 회의를 확정하고 홈 화면 일정에 추가할게요</p>
            <label htmlFor="meeting-title">회의 제목</label>
            <input
              id="meeting-title"
              value={meetingTitle}
              onChange={(event) => setMeetingTitle(event.target.value)}
            />
            <div className="tracker-modal__summary">
              <strong>🔴 일부 참석자에게 불편한 시간이에요</strong>
              {localTimes.map((person) => (
                <div key={person.id}>
                  <span><b>{person.name}</b> · 현지 {person.time}</span>
                  <span className={`recommendation-status recommendation-status--${person.status}`}>
                    ● {person.status === 'comfortable' ? '✅ 편한 시간' : '🔴 불편한 시간'}
                  </span>
                </div>
              ))}
            </div>
            <button className="tracker-modal__confirm" type="button" onClick={confirmMeeting}>
              확정하기
            </button>
          </section>
        </div>
      )}

      <div className={`tracker-toast${toast ? ' tracker-toast--visible' : ''}`} role="status">
        {toast}
      </div>
    </section>
  )
}

export default TrackerPage
