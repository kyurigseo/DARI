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
  const errorId = useId()
  const titleInputRef = useRef(null)
  const [title, setTitle] = useState('')
  const [date, setDate] = useState(initialDateTime.current.date)
  const [time, setTime] = useState(initialDateTime.current.time)
  const [selectedQuickTime, setSelectedQuickTime] = useState(null)
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
      // Meeting API가 일정 필드를 지원하기 전까지 선택한 날짜/시간은 UI state로만 관리한다.
      const createdMeeting = await createMeeting({
        title: trimmedTitle,
        room_code: createRoomCode(),
      })
      if (!createdMeeting?.room_code) {
        throw new Error('Created meeting has no room_code')
      }

      // TODO: 일정 API가 Meeting과 연결되면 Home 목록/Header 일정 badge를 갱신한다.
      navigate(`/meeting/${createdMeeting.room_code}`)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
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

          <p className="create-meeting-modal__guide">
            회의를 만든 뒤, 회의실 안에서 참가자를 초대할 수 있어요
          </p>
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
