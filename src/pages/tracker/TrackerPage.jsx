import { useEffect, useRef, useState } from 'react'
import { getMe } from '../../api/auth'
import {
  getLatestAlert,
  getParticipationSummary,
  getHeatmap,
  updateMyHeatmapSlot,
  getRecommendation,
  confirmMeeting as confirmMeetingApi,
} from '../../api/tracker'
import './TrackerPage.css'

const statusOrder = ['comfortable', 'normal', 'uncomfortable']
const timeLabels = Array.from({ length: 12 }, (_, index) => `${String(index * 2).padStart(2, '0')}:00`)
const todayWeekday = (new Date().getUTCDay() + 6) % 7 // JS: 0=일요일 -> 0=월요일 변환 (UTC 기준)

function statusFromBackend(value) {
  if (value === 'COMFORTABLE') return 'comfortable'
  if (value === 'UNCOMFORTABLE') return 'uncomfortable'
  if (value === 'NEUTRAL') return 'normal'
  return 'normal'
}

function statusToBackend(value) {
  if (value === 'comfortable') return 'COMFORTABLE'
  if (value === 'uncomfortable') return 'UNCOMFORTABLE'
  return 'NEUTRAL'
}

function TrackerPage() {
  const [finderExpanded, setFinderExpanded] = useState(false)
  const [me, setMe] = useState(null)
  const [alert, setAlert] = useState(null)
  const [participation, setParticipation] = useState([])
  const [heatmapRows, setHeatmapRows] = useState([])
  const [myRow, setMyRow] = useState(() => Array(48).fill('normal'))
  const [recommendation, setRecommendation] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [meetingTitle, setMeetingTitle] = useState('시차 조율 회의')
  const [confirmed, setConfirmed] = useState(false)
  const [toast, setToast] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const toastTimerRef = useRef(null)

  useEffect(() => {
    let isMounted = true

    async function load() {
      try {
        const user = await getMe()
        if (!isMounted) return
        setMe(user)

        const [alertData, participationData, heatmapData, recommendationData] = await Promise.all([
          getLatestAlert(),
          getParticipationSummary([user.id]),
          getHeatmap([user.id]),
          getRecommendation([user.id]),
        ])

        if (!isMounted) return
        setAlert(alertData)
        setParticipation(participationData.results ?? [])
        setRecommendation(recommendationData.recommendation)

        const rows = (heatmapData.results ?? []).map((heatmapRow) => {
          const row = Array(48).fill('normal')
          for (const slot of heatmapRow.slots) {
            if (slot.weekday === todayWeekday) {
              row[slot.half_hour_index] = statusFromBackend(slot.status)
            }
          }
          return { ...heatmapRow, cells: row }
        })
        setHeatmapRows(rows)
        const myHeatmapRow = rows.find((row) => row.user_id === user.id)
        if (myHeatmapRow) {
          setMyRow(myHeatmapRow.cells)
        }
      } catch {
        // 개별 위젯 실패는 화면 전체를 막지 않고 해당 섹션만 빈 상태로 둔다.
      } finally {
        if (isMounted) setIsLoading(false)
      }
    }

    load()
    return () => {
      isMounted = false
    }
  }, [])

  const cycleMyAvailability = async (cellIndex) => {
    const currentStatus = myRow[cellIndex]
    const nextStatus = statusOrder[(statusOrder.indexOf(currentStatus) + 1) % statusOrder.length]

    setMyRow((current) => current.map((status, index) => (index === cellIndex ? nextStatus : status)))
    setHeatmapRows((rows) =>
      rows.map((row) =>
        row.is_me
          ? { ...row, cells: row.cells.map((status, index) => (index === cellIndex ? nextStatus : status)) }
          : row,
      ),
    )

    try {
      await updateMyHeatmapSlot({
        weekday: todayWeekday,
        halfHourIndex: cellIndex,
        status: statusToBackend(nextStatus),
      })
    } catch {
      setMyRow((current) => current.map((status, index) => (index === cellIndex ? currentStatus : status)))
      setHeatmapRows((rows) =>
        rows.map((row) =>
          row.is_me
            ? { ...row, cells: row.cells.map((status, index) => (index === cellIndex ? currentStatus : status)) }
            : row,
        ),
      )
      showToast('시간대 변경에 실패했어요.')
    }
  }

  const showToast = (message) => {
    setToast(message)

    if (toastTimerRef.current) {
      clearTimeout(toastTimerRef.current)
    }

    toastTimerRef.current = setTimeout(() => setToast(''), 2500)
  }

  const confirmMeeting = async () => {
    if (!me || !recommendation) return

    try {
      await confirmMeetingApi({
        title: meetingTitle,
        weekday: recommendation.weekday,
        halfHourIndex: recommendation.half_hour_index,
        participantIds: recommendation.participants.map((participant) => participant.user_id),
      })
      setConfirmed(true)
      setModalOpen(false)
      showToast(`${recommendation.start_time_kst} 회의를 확정하고 홈에 추가했어요 ✅`)
    } catch {
      setModalOpen(false)
      showToast('일정 확정에 실패했어요. 다시 시도해주세요.')
    }
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

  if (isLoading) {
    return (
      <section className="tracker-page">
        <p>불러오는 중...</p>
      </section>
    )
  }

  return (
    <section className="tracker-page">
      <header className="tracker-page__heading">
        <h1>시차 형평성 트래커</h1>
        <p>참여 시간대 기록을 보고, 모두에게 공정한 회의 시간을 함께 찾아보세요</p>
      </header>

      {participation.length > 0 && (
        <section className="participation-card" aria-labelledby="participation-title">
          <h2 id="participation-title">최근 {participation[0]?.window ?? 6}회 참여 시간대</h2>
          <div className="participation-card__list">
            {participation.map((person, index) => {
              const dominant = Object.values(person.buckets).sort((a, b) => b.count - a.count)[0]
              return (
                <div
                  className={`participation-row participation-row--${['red', 'teal', 'orange', 'teal'][index % 4]}`}
                  key={person.user_id}
                >
                  <span className="participation-row__avatar">{person.user_id === me?.id ? '나' : person.username}</span>
                  <div className="participation-row__track" aria-hidden="true">
                    <span style={{ width: `${Math.round((dominant?.ratio ?? 0) * 100)}%` }} />
                  </div>
                  <span className="participation-row__badge">
                    {dominant?.label} {dominant?.count ?? 0}/{person.total_records}
                  </span>
                </div>
              )
            })}
          </div>
        </section>
      )}

      {alert?.has_alert && (
        <div className="tracker-warning">
          <span aria-hidden="true">⚠️</span>
          <span>{alert.message}</span>
        </div>
      )}

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

                {heatmapRows.map((person) => (
                  <div
                    className={`availability-row${person.is_me ? ' availability-row--me' : ''}`}
                    key={person.user_id}
                  >
                    <strong>{person.is_me ? '나' : person.username}</strong>
                    <div className="availability-row__cells">
                    {(person.is_me ? myRow : person.cells).map((status, index) => {
                      const time = `${String(Math.floor(index / 2)).padStart(2, '0')}:${index % 2 ? '30' : '00'}`

                      return person.is_me ? (
                        <button
                          className={`availability-cell availability-cell--${status}`}
                          type="button"
                          aria-label={`나 ${time}, ${status}. 클릭해서 변경`}
                          onClick={() => cycleMyAvailability(index)}
                          key={time}
                        />
                      ) : (
                        <span
                          className={`availability-cell availability-cell--${status}`}
                          aria-label={`${person.username} ${time}, ${status}`}
                          key={time}
                        />
                      )
                    })}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {recommendation && (
              <div className="recommendation-panel">
                <h3>
                  {confirmed ? '🔒 확정된 회의 시간' : '🏆 추천 시간대'} — {recommendation.start_time_kst}
                </h3>
                {recommendation.has_uncomfortable_participants && (
                  <p className="recommendation-panel__warning">🔴 일부 참석자에게 불편한 시간이에요</p>
                )}
                <div className="recommendation-panel__people">
                  {recommendation.participants.map((person) => (
                    <div key={person.user_id}>
                      <span>
                        <strong>{person.username}</strong> · 현지 {person.local_time}
                      </span>
                      <span className={`recommendation-status recommendation-status--${statusFromBackend(person.status)}`}>
                        ● {person.status === 'COMFORTABLE' ? '✅ 편한 시간' : person.status === 'NEUTRAL' ? '보통' : '🔴 불편한 시간'}
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
              </div>
            )}
          </div>
        )}
      </section>

      {modalOpen && recommendation && (
        <div className="tracker-modal-backdrop" onMouseDown={() => setModalOpen(false)}>
          <section
            className="tracker-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="tracker-modal-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <h2 id="tracker-modal-title">회의 일정 확정</h2>
            <p>{recommendation.start_time_kst}에 회의를 확정하고 홈 화면 일정에 추가할게요</p>
            <label htmlFor="meeting-title">회의 제목</label>
            <input
              id="meeting-title"
              value={meetingTitle}
              onChange={(event) => setMeetingTitle(event.target.value)}
            />
            <div className="tracker-modal__summary">
              {recommendation.has_uncomfortable_participants && (
                <strong>🔴 일부 참석자에게 불편한 시간이에요</strong>
              )}
              {recommendation.participants.map((person) => (
                <div key={person.user_id}>
                  <span>
                    <b>{person.username}</b> · 현지 {person.local_time}
                  </span>
                  <span className={`recommendation-status recommendation-status--${statusFromBackend(person.status)}`}>
                    ● {person.status === 'COMFORTABLE' ? '✅ 편한 시간' : person.status === 'NEUTRAL' ? '보통' : '🔴 불편한 시간'}
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
