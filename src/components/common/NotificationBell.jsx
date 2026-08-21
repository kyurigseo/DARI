import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getInvitations, respondInvitation } from '../../api/meetings'
import './NotificationBell.css'

const REFETCH_EVENT = 'dari:invitations-refetch'

// 다른 컴포넌트에서 알림 벨을 즉시 새로고침하고 싶을 때 쓸 수 있는 확장 지점.
// 지금은 아무도 호출하지 않지만(수락은 navigate로 페이지 이탈, 거절은 로컬 갱신으로 충분),
// 나중에 폴링 없이 다른 화면에서 트리거만 하고 싶을 때를 위해 export해둔다.
export function refetchInvitations() {
  window.dispatchEvent(new Event(REFETCH_EVENT))
}

function getInitial(name) {
  return name?.trim()?.slice(0, 1) || '?'
}

function formatRelativeTime(isoString) {
  if (!isoString) return ''
  const date = new Date(isoString)
  const diffMinutes = Math.floor((Date.now() - date.getTime()) / 60000)

  if (diffMinutes < 1) return '방금 전'
  if (diffMinutes < 60) return `${diffMinutes}분 전`

  const diffHours = Math.floor(diffMinutes / 60)
  if (diffHours < 24) return `${diffHours}시간 전`

  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 7) return `${diffDays}일 전`

  return date.toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' })
}

function getErrorMessage(error) {
  const message = error?.response?.data?.error || error?.response?.data?.message
  return typeof message === 'string'
    ? message
    : '초대 처리에 실패했어요. 잠시 후 다시 시도해주세요.'
}

function NotificationBell() {
  const navigate = useNavigate()
  const containerRef = useRef(null)
  const [invitations, setInvitations] = useState([])
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [selectedInvitation, setSelectedInvitation] = useState(null)
  const [isResponding, setIsResponding] = useState(false)
  const [respondError, setRespondError] = useState('')

  const loadInvitations = useCallback(async () => {
    try {
      const data = await getInvitations()
      setInvitations(Array.isArray(data) ? data : [])
    } catch {
      // 알림 벨은 항상 떠 있어야 하므로 조회 실패는 조용히 무시하고 배지 없이 둔다.
    }
  }, [])

  useEffect(() => {
    loadInvitations()
    window.addEventListener(REFETCH_EVENT, loadInvitations)
    return () => window.removeEventListener(REFETCH_EVENT, loadInvitations)
  }, [loadInvitations])

  useEffect(() => {
    if (!isDropdownOpen) return undefined

    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsDropdownOpen(false)
      }
    }
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') setIsDropdownOpen(false)
    }

    document.addEventListener('mousedown', handleClickOutside)
    window.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [isDropdownOpen])

  const openConfirm = (invitation) => {
    setRespondError('')
    setSelectedInvitation(invitation)
    setIsDropdownOpen(false)
  }

  const closeConfirm = () => {
    if (isResponding) return
    setSelectedInvitation(null)
    setRespondError('')
  }

  const handleAccept = async () => {
    if (!selectedInvitation || isResponding) return
    setIsResponding(true)
    setRespondError('')

    try {
      const data = await respondInvitation(selectedInvitation.meeting_id, 'accept')
      setInvitations((current) =>
        current.filter((invitation) => invitation.meeting_id !== selectedInvitation.meeting_id)
      )
      setSelectedInvitation(null)
      // 다른 페이지에 있었더라도 회의실로 이동하면서 HomePage는 자연스럽게 언마운트되고,
      // 나중에 "/"로 돌아오면 getDashboard()가 새로 호출되므로 별도 갱신 로직은 불필요하다.
      navigate(`/meeting/${data.room_code}`)
    } catch (err) {
      setRespondError(getErrorMessage(err))
      setIsResponding(false)
    }
  }

  const handleReject = async () => {
    if (!selectedInvitation || isResponding) return
    setIsResponding(true)
    setRespondError('')

    try {
      await respondInvitation(selectedInvitation.meeting_id, 'reject')
      setInvitations((current) =>
        current.filter((invitation) => invitation.meeting_id !== selectedInvitation.meeting_id)
      )
      setSelectedInvitation(null)
    } catch (err) {
      setRespondError(getErrorMessage(err))
    } finally {
      setIsResponding(false)
    }
  }

  return (
    <div className="notification-bell" ref={containerRef}>
      <button
        type="button"
        className="notification-bell__button"
        onClick={() => setIsDropdownOpen((open) => !open)}
        aria-label="알림"
        aria-haspopup="true"
        aria-expanded={isDropdownOpen}
      >
        <span aria-hidden="true">🔔</span>
        {invitations.length > 0 && (
          <span className="notification-bell__badge">{invitations.length}</span>
        )}
      </button>

      {isDropdownOpen && (
        <div className="notification-bell__dropdown" role="menu">
          <h3 className="notification-bell__dropdown-title">받은 회의 초대</h3>
          {invitations.length === 0 ? (
            <p className="notification-bell__empty">새로운 초대가 없어요</p>
          ) : (
            <ul className="notification-bell__list">
              {invitations.map((invitation) => (
                <li className="notification-bell__item" key={invitation.meeting_id}>
                  <span className="notification-bell__avatar" aria-hidden="true">
                    {getInitial(invitation.host_name)}
                  </span>
                  <div className="notification-bell__item-body">
                    <p className="notification-bell__item-title">{invitation.title}</p>
                    <p className="notification-bell__item-meta">
                      {invitation.host_name}님의 초대 · {formatRelativeTime(invitation.created_at)}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="notification-bell__confirm-button"
                    onClick={() => openConfirm(invitation)}
                  >
                    확인하기
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {selectedInvitation && (
        <div className="invite-confirm-overlay" onMouseDown={closeConfirm}>
          <section
            className="invite-confirm-card"
            role="dialog"
            aria-modal="true"
            aria-labelledby="invite-confirm-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <p className="invite-confirm-card__label">DARI 회의 초대</p>
            <span className="invite-confirm-card__avatar" aria-hidden="true">
              {getInitial(selectedInvitation.host_name)}
            </span>
            <h2 id="invite-confirm-title">{selectedInvitation.title}</h2>
            <p className="invite-confirm-card__message">
              {selectedInvitation.host_name}님이 나를 초대했어요
            </p>

            {respondError && (
              <p className="invite-confirm-card__error" role="alert">
                {respondError}
              </p>
            )}

            <div className="invite-confirm-card__actions">
              <button
                type="button"
                className="invite-confirm-card__reject"
                onClick={handleReject}
                disabled={isResponding}
              >
                거절
              </button>
              <button
                type="button"
                className="invite-confirm-card__accept"
                onClick={handleAccept}
                disabled={isResponding}
              >
                {isResponding ? '처리 중...' : '참가 수락'}
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  )
}

export default NotificationBell
