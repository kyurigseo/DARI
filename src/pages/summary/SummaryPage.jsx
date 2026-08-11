import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { meetingSummaries, teamMembers } from './summaryMockData'
import './SummaryPage.css'

const formatTimestamp = (date) => {
  const mm = date.getMonth() + 1
  const dd = date.getDate()
  const hh = String(date.getHours()).padStart(2, '0')
  const min = String(date.getMinutes()).padStart(2, '0')
  return `${mm}/${dd} ${hh}:${min} 저장됨`
}

const buildShareText = (meeting) => {
  const items = meeting.actionItems
    .map((item) => {
      const assigneeText = item.assignee
        ? ` (${item.assignee}${item.due ? ` · 마감 ${item.due}` : ''})`
        : ''
      return `- [${item.done ? '완료' : '진행중'}] ${item.label}${assigneeText}`
    })
    .join('\n')

  return `${meeting.title} · ${meeting.date}\n\n[AI 요약]\n${meeting.aiSummary}\n\n[Action Items]\n${items}`
}

function SummaryPage() {
  const { meetingId } = useParams()
  const navigate = useNavigate()

  const [meetings, setMeetings] = useState(meetingSummaries)
  const [notesByMeeting, setNotesByMeeting] = useState({})
  const [noteDraft, setNoteDraft] = useState('')
  const [toast, setToast] = useState(null)
  
  // 모달 상태
  const [assigneeTarget, setAssigneeTarget] = useState(null)
  const [dueTarget, setDueTarget] = useState(null)
  const [customAssignee, setCustomAssignee] = useState('')

  const toastTimerRef = useRef(null)

  const activeId = meetings.some((m) => m.id === meetingId) ? meetingId : meetings[0].id
  const activeMeeting = meetings.find((m) => m.id === activeId)
  const activeNotes = notesByMeeting[activeId] ?? []

  useEffect(() => () => clearTimeout(toastTimerRef.current), [])

  useEffect(() => {
    setNoteDraft('')
  }, [activeId])

  const showToast = (message) => {
    clearTimeout(toastTimerRef.current)
    setToast(message)
    toastTimerRef.current = setTimeout(() => setToast(null), 3000)
  }

  const updateMeeting = (id, updater) => {
    setMeetings((prev) => prev.map((meeting) => (meeting.id === id ? updater(meeting) : meeting)))
  }

  const handleTabClick = (id) => {
    navigate(`/summary/${id}`)
  }

  /* 메모 관련 */
  const handleSaveNote = () => {
    const text = noteDraft.trim()
    if (!text) return

    setNotesByMeeting((prev) => ({
      ...prev,
      [activeId]: [
        { id: `note-${Date.now()}`, text, timestamp: formatTimestamp(new Date()) },
        ...(prev[activeId] ?? []),
      ],
    }))
    setNoteDraft('')
  }

  const handleDeleteNote = (noteId) => {
    setNotesByMeeting((prev) => ({
      ...prev,
      [activeId]: (prev[activeId] ?? []).filter((note) => note.id !== noteId),
    }))
  }

  /* Action Item 관련 */
  const toggleActionItem = (itemId) => {
    updateMeeting(activeId, (meeting) => ({
      ...meeting,
      actionItems: meeting.actionItems.map((item) =>
        item.id === itemId ? { ...item, done: !item.done } : item,
      ),
    }))
  }

  const assignMember = (itemId, memberName) => {
    if (!memberName.trim()) return

    updateMeeting(activeId, (meeting) => ({
      ...meeting,
      actionItems: meeting.actionItems.map((item) =>
        item.id === itemId ? { ...item, assignee: memberName.trim() } : item,
      ),
    }))
    showToast(`${memberName.trim()}님을 담당자로 지정했어요✅`)
    setAssigneeTarget(null)
    setCustomAssignee('')
  }

  const setDueDate = (itemId, month, day) => {
    const dueText = `${Number(month)}/${Number(day)}`
    updateMeeting(activeId, (meeting) => ({
      ...meeting,
      actionItems: meeting.actionItems.map((item) =>
        item.id === itemId ? { ...item, due: dueText } : item,
      ),
    }))
    showToast(`마감 기한을 ${dueText}로 설정했어요📅`)
    setDueTarget(null)
  }

  const handleDateInput = (itemId, value) => {
    if (!value) return
    const [, month, day] = value.split('-')
    setDueDate(itemId, month, day)
  }

  const handlePresetDue = (itemId, daysToAdd) => {
    const d = new Date()
    d.setDate(d.getDate() + daysToAdd)
    const month = d.getMonth() + 1
    const day = d.getDate()
    setDueDate(itemId, month, day)
  }

  /* 공유 관련 */
  const handleEmailShare = () => {
    const subject = encodeURIComponent(`${activeMeeting.title} · ${activeMeeting.date}`)
    const body = encodeURIComponent(buildShareText(activeMeeting))
    window.location.href = `mailto:?subject=${subject}&body=${body}`
    showToast('메일 앱을 열었어요 ✉️ 제목·본문이 자동으로 채워져요')
  }

  const handleSlackShare = async () => {
    try {
      await navigator.clipboard.writeText(buildShareText(activeMeeting))
    } catch (error) {
      console.warn('클립보드 복사 실패', error)
    }
    showToast('Slack에 붙여넣기 좋은 형식으로 복사했어요 📋 채널에 붙여넣기만 하면 돼요')
  }

  return (
    <section className="summary-page">
      <header className="summary-page__heading">
        <h1>회의 요약 &amp; Action Item</h1>
        <p>진행했던 회의 중 하나를 골라 요약과 할 일을 확인하세요</p>
      </header>

      <div className="meeting-tabs" role="tablist" aria-label="회의 선택">
        {meetings.map((meeting) => {
          const isActive = meeting.id === activeId

          return (
            <button
              className={`meeting-tab${isActive ? ' meeting-tab--active' : ''}`}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => handleTabClick(meeting.id)}
              key={meeting.id}
            >
              {meeting.title} · {meeting.date}
            </button>
          )
        })}
      </div>

      <article className="summary-card">
        <h2 className="summary-card__title">
          {activeMeeting.title} · {activeMeeting.date}
        </h2>
        <p className="summary-card__ai-label">🤖 AI 요약</p>
        <p className="summary-card__text">{activeMeeting.aiSummary}</p>
      </article>

      <article className="note-card">
        <h2 className="note-card__title">✍️ 내 메모 · 직접 요약</h2>
        <textarea
          className="note-card__textarea"
          value={noteDraft}
          onChange={(event) => setNoteDraft(event.target.value)}
          placeholder="회의에서 느낀 점이나 AI 요약에 없는 내용을 자유롭게 적어보세요"
        />
        <div className="note-card__actions">
          <button
            className="note-card__save"
            type="button"
            onClick={handleSaveNote}
            disabled={!noteDraft.trim()}
          >
            메모 저장
          </button>
        </div>

        <div className="note-card__divider" />

        <h3 className="note-card__list-title">저장된 메모 목록</h3>
        {activeNotes.length === 0 ? (
          <p className="note-card__empty">아직 저장된 메모가 없어요. 위에 적고 저장을 눌러보세요</p>
        ) : (
          <ul className="note-list">
            {activeNotes.map((note) => (
              <li className="note-item" key={note.id}>
                <div className="note-item__body">
                  <p className="note-item__text">{note.text}</p>
                  <span className="note-item__timestamp">🕒 {note.timestamp}</span>
                </div>
                <button
                  className="note-item__delete"
                  type="button"
                  aria-label="메모 삭제"
                  onClick={() => handleDeleteNote(note.id)}
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}
      </article>

      <article className="action-card">
        <h2 className="action-card__title">
          <span aria-hidden="true">✅</span> Action Items
        </h2>
        <ul className="action-list">
          {activeMeeting.actionItems.map((item) => (
            <li className="action-item" key={item.id}>
              <label className="action-item__check">
                <input
                  type="checkbox"
                  checked={item.done}
                  onChange={() => toggleActionItem(item.id)}
                />
                <span className="action-item__box" aria-hidden="true">
                  {item.done ? '✓' : ''}
                </span>
                <span className={`action-item__label${item.done ? ' action-item__label--done' : ''}`}>
                  {item.label}
                </span>
              </label>

              <div className="action-item__meta">
                {item.assignee ? (
                  <button
                    className="action-tag action-tag--assignee"
                    type="button"
                    onClick={() => setAssigneeTarget(item.id)}
                  >
                    {item.assignee}
                  </button>
                ) : (
                  <button
                    className="action-tag-button action-tag-button--assignee"
                    type="button"
                    onClick={() => setAssigneeTarget(item.id)}
                  >
                    담당자 지정
                  </button>
                )}

                {item.due ? (
                  <button
                    className="action-tag action-tag--due"
                    type="button"
                    onClick={() => setDueTarget(item.id)}
                  >
                    {item.due}
                  </button>
                ) : (
                  <button
                    className="action-tag-button action-tag-button--due"
                    type="button"
                    onClick={() => setDueTarget(item.id)}
                  >
                    기한 지정
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      </article>

      <div className="share-row">
        <button className="share-button share-button--outline" type="button" onClick={handleEmailShare}>
          📧 메일로 공유
        </button>
        <button className="share-button share-button--primary" type="button" onClick={handleSlackShare}>
          💬 Slack으로 공유
        </button>
      </div>

{/* 담당자 지정 모달 */}
      {assigneeTarget && (
        <div className="summary-modal-overlay" onClick={() => { setAssigneeTarget(null); setCustomAssignee(''); }}>
          <div className="summary-modal summary-modal--assignee" onClick={(event) => event.stopPropagation()}>
            <h3 className="summary-modal__title">담당자 지정</h3>
            
            <p className="summary-modal__subtitle">회의 참석자 중에서 선택</p>
            <ul className="member-list">
              {teamMembers.map((member) => (
                <li key={member.id}>
                  <button
                    className="member-list__button"
                    type="button"
                    onClick={() => assignMember(assigneeTarget, member.name)}
                  >
                    {member.name}
                    {member.name === '나' && <span className="host-badge">호스트</span>}
                  </button>
                </li>
              ))}
            </ul>

            <p className="summary-modal__subtitle">참석자 목록에 없다면 직접 추가</p>
            <div className="summary-modal__input-row">
              <input 
                type="text" 
                placeholder="이름 입력" 
                value={customAssignee}
                onChange={(e) => setCustomAssignee(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && assignMember(assigneeTarget, customAssignee)}
              />
              <button type="button" onClick={() => assignMember(assigneeTarget, customAssignee)}>지정</button>
            </div>
          </div>
        </div>
      )}

      {/* 기한 지정 모달 */}
      {dueTarget && (
        <div className="summary-modal-overlay" onClick={() => setDueTarget(null)}>
          <div className="summary-modal summary-modal--due" onClick={(event) => event.stopPropagation()}>
            <h3 className="summary-modal__title">마감 기한 설정</h3>
            
            <div className="preset-btn-group-row">
              <button type="button" className="preset-btn" onClick={() => handlePresetDue(dueTarget, 0)}>오늘</button>
              <button type="button" className="preset-btn" onClick={() => handlePresetDue(dueTarget, 1)}>내일</button>
              <button type="button" className="preset-btn" onClick={() => handlePresetDue(dueTarget, 7)}>1주일 후</button>
            </div>

            <p className="summary-modal__subtitle summary-modal__subtitle--due">직접 날짜 선택</p>
            <div className="summary-modal__input-row summary-modal__input-row--due">
              <input
                id="due-date-input"
                type="date"
              />
              <button 
                type="button" 
                onClick={() => {
                  const val = document.getElementById('due-date-input').value;
                  if (val) {
                    handleDateInput(dueTarget, val);
                  } else {
                    setDueTarget(null);
                  }
                }}
              >
                설정
              </button>
            </div>
          </div>
        </div>
      )}

      <div className={`summary-toast${toast ? ' summary-toast--visible' : ''}`} role="status">
        {toast}
      </div>
    </section>
  )
}

export default SummaryPage