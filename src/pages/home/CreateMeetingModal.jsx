import { useEffect, useId, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createMeeting } from '../../api/meetings'

function formatLocalDateTime(value) {
  const pad = (number) => String(number).padStart(2, '0')

  return {
    date: `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}`,
    time: `${pad(value.getHours())}:${pad(value.getMinutes())}`,
  }
}

function createRoomCode() {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID()

  const bytes = crypto.getRandomValues(new Uint8Array(16))
  bytes[6] = (bytes[6] & 0x0f) | 0x40
  bytes[8] = (bytes[8] & 0x3f) | 0x80
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

function isValidDateTime(date, time) {
  const dateMatch = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date)
  const timeMatch = /^(\d{2}):(\d{2})$/.exec(time)
  if (!dateMatch || !timeMatch) return false

  const [, year, month, day] = dateMatch.map(Number)
  const [, hours, minutes] = timeMatch.map(Number)
  const value = new Date(year, month - 1, day, hours, minutes)

  return (
    value.getFullYear() === year &&
    value.getMonth() === month - 1 &&
    value.getDate() === day &&
    value.getHours() === hours &&
    value.getMinutes() === minutes
  )
}

function getApiErrorMessage(error) {
  const data = error?.response?.data
  const message = data?.error || data?.message || data?.detail
  return typeof message === 'string'
    ? message
    : '회의를 만들지 못했어요. 잠시 후 다시 시도해주세요.'
}

function CreateMeetingModal({ onClose }) {
  const navigate = useNavigate()
  const initialDateTime = useRef(formatLocalDateTime(new Date()))
  const titleId = useId()
  const dateId = useId()
  const timeId = useId()
  const participantId = useId()
  const errorId = useId()
  const titleInputRef = useRef(null)
  const [title, setTitle] = useState('')
  const [date, setDate] = useState(initialDateTime.current.date)
  const [time, setTime] = useState(initialDateTime.current.time)
  const [selectedQuickTime, setSelectedQuickTime] = useState(null)
  const [participantInput, setParticipantInput] = useState('')
  const [participants, setParticipants] = useState([])
  const [error, setError] = useState('')
  const [isCreating, setIsCreating] = useState(false)

  useEffect(() => {
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    titleInputRef.current?.focus()

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeyDown)

    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [onClose])

  const selectQuickTime = (quickTime, minutesToAdd) => {
    const selected = new Date(Date.now() + minutesToAdd * 60 * 1000)
    const next = formatLocalDateTime(selected)
    setDate(next.date)
    setTime(next.time)
    setSelectedQuickTime(quickTime)
    setError('')
  }

  const addParticipant = () => {
    const trimmed = participantInput.trim()
    if (!trimmed || participants.includes(trimmed)) {
      setParticipantInput('')
      return
    }
    setParticipants((current) => [...current, trimmed])
    setParticipantInput('')
  }

  const removeParticipant = (username) => {
    setParticipants((current) => current.filter((name) => name !== username))
  }

  const handleParticipantKeyDown = (event) => {
    if (event.key !== 'Enter') return
    event.preventDefault()
    addParticipant()
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (isCreating) return

    const trimmedTitle = title.trim()
    if (!trimmedTitle) {
      setError('회의 제목을 입력해주세요.')
      titleInputRef.current?.focus()
      return
    }
    if (!isValidDateTime(date, time)) {
      setError('유효한 날짜와 시간을 입력해주세요.')
      return
    }

    setError('')
    setIsCreating(true)

    try {
      const createdMeeting = await createMeeting({
        title: trimmedTitle,
        room_code: createRoomCode(),
        scheduled_start_time: `${date}T${time}:00`,
        participants,
      })
      if (!createdMeeting?.room_code) {
        throw new Error('Created meeting has no room_code')
      }

      navigate(`/meeting/${createdMeeting.room_code}`)
    } catch (requestError) {
      // 존재하지 않는 참가자 username은 백엔드가 404 + { error, username }으로 응답하므로
      // 어떤 이름이 문제인지 알 수 있게 별도로 처리한다.
      const invalidUsername = requestError?.response?.data?.username
      setError(
        invalidUsername
          ? `존재하지 않는 사용자: ${invalidUsername}`
          : getApiErrorMessage(requestError)
      )
      setIsCreating(false)
    }
  }

  return (
    <div className="create-meeting-overlay" onMouseDown={onClose}>
      <section
        className="create-meeting-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-meeting-title"
        aria-describedby={error ? errorId : undefined}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <h2 id="create-meeting-title">새 회의 만들기</h2>
        <form onSubmit={handleSubmit} noValidate>
          <label htmlFor={titleId}>회의 제목</label>
          <input
            ref={titleInputRef}
            id={titleId}
            type="text"
            value={title}
            placeholder="예) 주간 팀 스탠드업"
            aria-invalid={Boolean(error && !title.trim())}
            onChange={(event) => {
              setTitle(event.target.value)
              setError('')
            }}
          />

          <div className="create-meeting-modal__date-time">
            <div>
              <label htmlFor={dateId}>날짜</label>
              <input
                id={dateId}
                type="date"
                value={date}
                onChange={(event) => {
                  setDate(event.target.value)
                  setSelectedQuickTime(null)
                  setError('')
                }}
              />
            </div>
            <div>
              <label htmlFor={timeId}>시간</label>
              <input
                id={timeId}
                type="time"
                value={time}
                onChange={(event) => {
                  setTime(event.target.value)
                  setSelectedQuickTime(null)
                  setError('')
                }}
              />
            </div>
          </div>

          <fieldset className="create-meeting-modal__quick-times">
            <legend>빠른 시간 선택</legend>
            <div>
              <button
                type="button"
                className={selectedQuickTime === 'now' ? 'is-active' : ''}
                aria-pressed={selectedQuickTime === 'now'}
                onClick={() => selectQuickTime('now', 0)}
              >
                지금 바로
              </button>
              <button
                type="button"
                className={selectedQuickTime === '30-minutes' ? 'is-active' : ''}
                aria-pressed={selectedQuickTime === '30-minutes'}
                onClick={() => selectQuickTime('30-minutes', 30)}
              >
                30분 후
              </button>
              <button
                type="button"
                className={selectedQuickTime === '1-hour' ? 'is-active' : ''}
                aria-pressed={selectedQuickTime === '1-hour'}
                onClick={() => selectQuickTime('1-hour', 60)}
              >
                1시간 후
              </button>
            </div>
          </fieldset>

          <div className="create-meeting-modal__participants">
            <label htmlFor={participantId}>참가자 초대 (선택)</label>
            <div className="create-meeting-modal__participant-row">
              <input
                id={participantId}
                type="text"
                value={participantInput}
                placeholder="이름 입력 후 추가"
                onChange={(event) => setParticipantInput(event.target.value)}
                onKeyDown={handleParticipantKeyDown}
              />
              <button
                type="button"
                className="create-meeting-modal__add-button"
                onClick={addParticipant}
              >
                추가
              </button>
            </div>
            {participants.length > 0 && (
              <div className="create-meeting-modal__chips">
                {participants.map((username) => (
                  <span className="create-meeting-modal__chip" key={username}>
                    {username}
                    <button
                      type="button"
                      className="create-meeting-modal__chip-remove"
                      aria-label={`${username} 삭제`}
                      onClick={() => removeParticipant(username)}
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          <p className="create-meeting-modal__guide">참가자에게 초대 알림이 전송돼요</p>
          {error && (
            <p className="create-meeting-modal__error" id={errorId} role="alert">
              {error}
            </p>
          )}
          <button className="create-meeting-modal__submit" type="submit" disabled={isCreating}>
            {isCreating ? '회의 만드는 중...' : '회의 만들기'}
          </button>
        </form>
      </section>
    </div>
  )
}

export default CreateMeetingModal
