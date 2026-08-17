import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  getSummaryTabs,
  getMeetingReport,
  createMemo,
  deleteMemo,
  updateActionItem,
  getShareText,
} from '../../api/meetings'
import './SummaryPage.css'

function SummaryPage() {
  const { meetingId: roomCode } = useParams()
  const navigate = useNavigate()

  const [tabs, setTabs] = useState([])
  const [selectedRoomCode, setSelectedRoomCode] = useState(null)
  const [report, setReport] = useState(null)
  const [noteDraft, setNoteDraft] = useState('')
  const [toast, setToast] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

  const [assigneeTarget, setAssigneeTarget] = useState(null)
  const [dueTarget, setDueTarget] = useState(null)
  const [customAssignee, setCustomAssignee] = useState('')

  const toastTimerRef = useRef(null)

  useEffect(() => {
    let isMounted = true

    getSummaryTabs()
      .then((data) => {
        if (!isMounted) return
        setTabs(data)
        const validRoomCodes = new Set(data.map((tab) => tab.room_code).filter(Boolean))
        const nextRoomCode = roomCode && validRoomCodes.has(roomCode)
          ? roomCode
          : data.find((tab) => tab.room_code)?.room_code

        setSelectedRoomCode(nextRoomCode || null)
        if (nextRoomCode && nextRoomCode !== roomCode) {
          navigate(`/summary/${nextRoomCode}`, { replace: true })
        }
      })
      .catch(() => {})

    return () => {
      isMounted = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!selectedRoomCode) return undefined
    let isMounted = true
    let pollTimer = null
    let pollCount = 0
    setIsLoading(true)
    setNoteDraft('')

    const loadReport = () => {
      getMeetingReport(selectedRoomCode)
        .then((data) => {
          if (!isMounted) return
          setReport(data)
          setIsLoading(false)
          if (data.ai_summary === '아직 생성된 회의 요약이 없습니다.' && pollCount < 15) {
            pollCount += 1
            pollTimer = setTimeout(loadReport, 2000)
          }
        })
        .catch(() => {
          if (isMounted) {
            setIsLoading(false)
            showToast('회의 정보를 불러오지 못했어요.')
          }
        })
    }
    loadReport()

    return () => {
      isMounted = false
      clearTimeout(pollTimer)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedRoomCode])

  useEffect(() => () => clearTimeout(toastTimerRef.current), [])

  const showToast = (message) => {
    clearTimeout(toastTimerRef.current)
    setToast(message)
    toastTimerRef.current = setTimeout(() => setToast(null), 3000)
  }

  const handleTabClick = (code) => {
    setSelectedRoomCode(code)
    navigate(`/summary/${code}`)
  }

  /* 메모 관련 */
  const handleSaveNote = async () => {
    const text = noteDraft.trim()
    if (!text || !roomCode) return

    try {
      const memo = await createMemo(roomCode, text)
      setReport((prev) => ({ ...prev, memos: [memo, ...prev.memos] }))
      setNoteDraft('')
    } catch {
      showToast('메모 저장에 실패했어요.')
    }
  }

  const handleDeleteNote = async (memoId) => {
    const previous = report
    setReport((prev) => ({ ...prev, memos: prev.memos.filter((note) => note.id !== memoId) }))

    try {
      await deleteMemo(memoId)
    } catch {
      setReport(previous)
      showToast('메모 삭제에 실패했어요.')
    }
  }

  /* Action Item 관련 */
  const toggleActionItem = async (item) => {
    const previous = report
    setReport((prev) => ({
      ...prev,
      action_items: prev.action_items.map((i) =>
        i.id === item.id ? { ...i, is_completed: !i.is_completed } : i,
      ),
    }))

    try {
      await updateActionItem(item.id, { is_completed: !item.is_completed })
    } catch {
      setReport(previous)
      showToast('업데이트에 실패했어요.')
    }
  }

  const assignMember = async (itemId, memberName) => {
    const name = memberName.trim()
    if (!name) return

    try {
      const updated = await updateActionItem(itemId, { assignee: name })
      setReport((prev) => ({
        ...prev,
        action_items: prev.action_items.map((i) => (i.id === itemId ? updated : i)),
      }))
      showToast(`${name}님을 담당자로 지정했어요✅`)
    } catch {
      showToast('담당자 지정에 실패했어요.')
    } finally {
      setAssigneeTarget(null)
      setCustomAssignee('')
    }
  }

  const setDueDate = async (itemId, isoDate, displayText) => {
    try {
      const updated = await updateActionItem(itemId, { due_date: isoDate })
      setReport((prev) => ({
        ...prev,
        action_items: prev.action_items.map((i) => (i.id === itemId ? updated : i)),
      }))
      showToast(`마감 기한을 ${displayText}로 설정했어요📅`)
    } catch {
      showToast('마감 기한 설정에 실패했어요.')
    } finally {
      setDueTarget(null)
    }
  }

  const toIsoDate = (date) => {
    const y = date.getFullYear()
    const m = String(date.getMonth() + 1).padStart(2, '0')
    const d = String(date.getDate()).padStart(2, '0')
    return `${y}-${m}-${d}`
  }

  const handleDateInput = (itemId, value) => {
    if (!value) return
    const [, month, day] = value.split('-')
    setDueDate(itemId, value, `${Number(month)}/${Number(day)}`)
  }

  const handlePresetDue = (itemId, daysToAdd) => {
    const d = new Date()
    d.setDate(d.getDate() + daysToAdd)
    setDueDate(itemId, toIsoDate(d), `${d.getMonth() + 1}/${d.getDate()}`)
  }

  /* 공유 관련 */
  const handleEmailShare = async () => {
    try {
      const data = await getShareText(roomCode)
      window.location.href = data.mailto_link
      showToast('메일 앱을 열었어요 ✉️ 제목·본문이 자동으로 채워져요')
    } catch {
      showToast('공유 텍스트를 가져오지 못했어요.')
    }
  }

  const handleSlackShare = async () => {
    try {
      const data = await getShareText(roomCode)
      await navigator.clipboard.writeText(data.formatted_text)
      showToast('Slack에 붙여넣기 좋은 형식으로 복사했어요 📋 채널에 붙여넣기만 하면 돼요')
    } catch {
      showToast('복사에 실패했어요.')
    }
  }

  if (isLoading || !report) {
    return (
      <section className="summary-page">
        <p>불러오는 중...</p>
      </section>
    )
  }

  return (
    <section className="summary-page">
      <header className="summary-page__heading">
        <h1>회의 요약 &amp; Action Item</h1>
        <p>진행했던 회의 중 하나를 골라 요약과 할 일을 확인하세요</p>
      </header>

      <div className="meeting-tabs" role="tablist" aria-label="회의 선택">
        {tabs.map((tab) => {
          const isActive = tab.room_code === roomCode

          return (
            <button
              className={`meeting-tab${isActive ? ' meeting-tab--active' : ''}`}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => handleTabClick(tab.room_code)}
              key={tab.room_code}
            >
              {tab.tab_title}
            </button>
          )
        })}
      </div>

      <article className="summary-card">
        <h2 className="summary-card__title">{report.display_header}</h2>
        <p className="summary-card__ai-label">🤖 AI 요약</p>
        <p className="summary-card__text">{report.ai_summary}</p>
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
        {report.memos.length === 0 ? (
          <p className="note-card__empty">아직 저장된 메모가 없어요. 위에 적고 저장을 눌러보세요</p>
        ) : (
          <ul className="note-list">
            {report.memos.map((note) => (
              <li className="note-item" key={note.id}>
                <div className="note-item__body">
                  <p className="note-item__text">{note.content}</p>
                  <span className="note-item__timestamp">🕒 {note.formatted_created_at}</span>
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
          {report.action_items.map((item) => (
            <li className="action-item" key={item.id}>
              <label className="action-item__check">
                <input
                  type="checkbox"
                  checked={item.is_completed}
                  onChange={() => toggleActionItem(item)}
                />
                <span className="action-item__box" aria-hidden="true">
                  {item.is_completed ? '✓' : ''}
                </span>
                <span className={`action-item__label${item.is_completed ? ' action-item__label--done' : ''}`}>
                  {item.task}
                </span>
              </label>

              <div className="action-item__meta">
                {item.assignee && item.assignee !== '미지정' ? (
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

                {item.formatted_due_date ? (
                  <button
                    className="action-tag action-tag--due"
                    type="button"
                    onClick={() => setDueTarget(item.id)}
                  >
                    {item.formatted_due_date}
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

      {assigneeTarget && (
        <div className="summary-modal-overlay" onClick={() => { setAssigneeTarget(null); setCustomAssignee(''); }}>
          <div className="summary-modal summary-modal--assignee" onClick={(event) => event.stopPropagation()}>
            <h3 className="summary-modal__title">담당자 지정</h3>

            <p className="summary-modal__subtitle">회의 참석자 중에서 선택</p>
            <ul className="member-list">
              {report.participants.map((member) => (
                <li key={member.name}>
                  <button
                    className="member-list__button"
                    type="button"
                    onClick={() => assignMember(assigneeTarget, member.name)}
                  >
                    {member.name}
                    {member.is_host && <span className="host-badge">호스트</span>}
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
