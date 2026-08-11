import { useEffect, useRef, useState } from 'react'
import {
  captionScript,
  initialChatMessages,
  initialParticipants,
  speechCards,
  translationLanguages,
  waitingList,
} from './meetingMockData'
import './MeetingPage.css'

const MEETING_TITLE = 'Acme Corp 협상'
const AVATAR_COLORS = ['#8454f6', '#e0546b', '#12b8a6', '#ff9351', '#4f8cff']

const TABS = [
  { id: 'subtitle', label: '자막·번역' },
  { id: 'cards', label: '발언카드' },
  { id: 'participants', label: '참가자' },
  { id: 'chat', label: '채팅' },
]

const formatElapsed = (totalSeconds) => {
  const minutes = Math.floor(totalSeconds / 60)
    .toString()
    .padStart(2, '0')
  const seconds = (totalSeconds % 60).toString().padStart(2, '0')
  return `${minutes}:${seconds}`
}

function MeetingPage() {
  const [joined, setJoined] = useState(false)
  const [micOn, setMicOn] = useState(false)
  const [cameraOn, setCameraOn] = useState(false)
  const [participants, setParticipants] = useState(initialParticipants)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [activeTab, setActiveTab] = useState('subtitle')
  const [selectedLang, setSelectedLang] = useState('한국어')
  const [liveSubtitles, setLiveSubtitles] = useState(true)
  const [captionIndex, setCaptionIndex] = useState(0)
  const [chatMessages, setChatMessages] = useState(initialChatMessages)
  const [chatDraft, setChatDraft] = useState('')
  const [inviteName, setInviteName] = useState('')
  const [toast, setToast] = useState('')

  const toastTimerRef = useRef(null)
  const chatLogRef = useRef(null)

  useEffect(() => {
    if (!joined) return undefined

    const timer = setInterval(() => setElapsedSeconds((prev) => prev + 1), 1000)
    const captionTimer = setInterval(
      () => setCaptionIndex((prev) => (prev + 1) % captionScript.length),
      6000,
    )

    return () => {
      clearInterval(timer)
      clearInterval(captionTimer)
    }
  }, [joined])

  useEffect(() => {
    if (chatLogRef.current) {
      chatLogRef.current.scrollTop = chatLogRef.current.scrollHeight
    }
  }, [chatMessages])

  useEffect(
    () => () => {
      if (toastTimerRef.current) {
        clearTimeout(toastTimerRef.current)
      }
    },
    [],
  )

  const showToast = (message) => {
    setToast(message)

    if (toastTimerRef.current) {
      clearTimeout(toastTimerRef.current)
    }

    toastTimerRef.current = setTimeout(() => setToast(''), 2500)
  }

  const handleJoin = () => {
    setJoined(true)
    setElapsedSeconds(0)
    setCaptionIndex(0)
    setActiveTab('subtitle')
    setParticipants((prev) => prev.map((p) => (p.isMe ? { ...p, micOn, cameraOn } : p)))
    showToast('회의에 참가했어요 🎉')

    // TODO: 실제 미디어 연결(WebRTC) API 명세 확정 후 스트림 연결 로직을 추가합니다.
  }

  const handleLeave = () => {
    setJoined(false)
    setElapsedSeconds(0)
  }

  const handleToggleMic = () => {
    const next = !micOn
    setMicOn(next)
    setParticipants((prev) => prev.map((p) => (p.isMe ? { ...p, micOn: next } : p)))
  }

  const handleToggleCamera = () => {
    const next = !cameraOn
    setCameraOn(next)
    setParticipants((prev) => prev.map((p) => (p.isMe ? { ...p, cameraOn: next } : p)))
  }

  const handleRemoveParticipant = (participantId) => {
    const target = participants.find((p) => p.id === participantId)
    setParticipants((prev) => prev.filter((p) => p.id !== participantId))
    if (target) showToast(`${target.name}님을 내보냈어요`)
  }

  const handleInvite = () => {
    const trimmed = inviteName.trim()
    if (!trimmed) return

    setParticipants((prev) => [
      ...prev,
      {
        id: `guest-${Date.now()}`,
        name: trimmed,
        tzIcon: '🌐',
        localTime: '--:--',
        color: AVATAR_COLORS[participants.length % AVATAR_COLORS.length],
        micOn: false,
        cameraOn: false,
        speaking: false,
      },
    ])
    setInviteName('')
    showToast(`${trimmed}님을 초대했어요`)

    // TODO: 초대 API 명세 확정 후 실제 초대 로직으로 교체합니다.
  }

  const handlePasteToChat = (card) => {
    setChatDraft(card.korean)
    setActiveTab('chat')
  }

  const handleSendMessage = (event) => {
    event.preventDefault()
    const trimmed = chatDraft.trim()
    if (!trimmed) return

    setChatMessages((prev) => [...prev, { id: `msg-${Date.now()}`, sender: '나', text: trimmed }])
    setChatDraft('')
  }

  const caption = captionScript[captionIndex]

  return (
    <section className="meeting-page">
      <header className="meeting-page__heading">
        <h1>실시간 회의 — {MEETING_TITLE}</h1>
        <p>DARI 안에서 바로 화상회의를 진행해요. 참가자 초대·내보내기도 여기서 할 수 있어요</p>
      </header>

      <div className="meeting-layout">
        {joined ? (
          <div className="call-stage">
            <div className="call-stage__topbar">
              <span className="rec-indicator">
                <span className="rec-indicator__dot" /> REC
              </span>
              <span className="call-stage__meta">🕐 {formatElapsed(elapsedSeconds)}</span>
              <span className="call-stage__meta">👥 {participants.length}명 참여 중</span>
            </div>

            <div className="video-grid">
              {participants.map((participant) => (
                <div
                  className={`video-tile${participant.speaking ? ' video-tile--speaking' : ''}`}
                  key={participant.id}
                >
                  <span className="video-tile__badge">
                    {participant.tzIcon} {participant.localTime}
                  </span>
                  <span className="video-tile__avatar" style={{ background: participant.color }}>
                    {participant.isMe ? '나' : participant.name.slice(0, 1)}
                  </span>
                  <span className="video-tile__footer">
                    <span className="video-tile__name">{participant.name}</span>
                    {participant.speaking ? (
                      <span className="video-tile__speaking">🎙️ 말하는 중</span>
                    ) : (
                      <span className={`video-tile__icon${participant.micOn ? '' : ' is-muted'}`}>
                        {participant.micOn ? '🔊' : '🔇'}
                      </span>
                    )}
                    {!participant.cameraOn && <span className="video-tile__icon">🚫</span>}
                  </span>
                </div>
              ))}
            </div>

            {liveSubtitles && (
              <div className="caption-bar">
                <p className="caption-bar__original">원문 · &quot;{caption.original}&quot;</p>
                <p className="caption-bar__translated">번역 · &quot;{caption.translated}&quot;</p>
              </div>
            )}

            <div className="call-toolbar">
              <button type="button" className="toolbar-btn" onClick={handleToggleMic}>
                🎤 {micOn ? '음소거' : '음소거 해제'}
              </button>
              <button type="button" className="toolbar-btn" onClick={handleToggleCamera}>
                📷 카메라 {cameraOn ? '끄기' : '켜기'}
              </button>
              <button type="button" className="toolbar-btn">
                🖥️ 화면공유
              </button>
              <button
                type="button"
                className={`toolbar-btn${activeTab === 'participants' ? ' is-active' : ''}`}
                onClick={() => setActiveTab('participants')}
              >
                👥 참가자
              </button>
              <button
                type="button"
                className={`toolbar-btn${activeTab === 'chat' ? ' is-active' : ''}`}
                onClick={() => setActiveTab('chat')}
              >
                💬 채팅
              </button>
              <button type="button" className="toolbar-btn toolbar-btn--danger" onClick={handleLeave}>
                📞 나가기
              </button>
            </div>
          </div>
        ) : (
          <div className="call-stage call-stage--prejoin">
            <div className="prejoin-preview">
              <span className="prejoin-preview__avatar">나</span>
              <span className="prejoin-preview__label">
                나{micOn ? '🎤' : '🔇'}{cameraOn ? '📷' : '🚫'}  
              </span>
            </div>

            <div className="prejoin-controls">
              <button
                type="button"
                className={`toggle-btn${micOn ? ' is-on' : ''}`}
                onClick={() => setMicOn((prev) => !prev)}
              >
                🎤 마이크 {micOn ? '켜짐' : '꺼짐'}
              </button>
              <button
                type="button"
                className={`toggle-btn${cameraOn ? ' is-on' : ''}`}
                onClick={() => setCameraOn((prev) => !prev)}
              >
                📷 카메라 {cameraOn ? '켜짐' : '꺼짐'}
              </button>
            </div>

            <button type="button" className="join-btn" onClick={handleJoin}>
              회의 참가하기 →
            </button>
          </div>
        )}

        {joined ? (
          <aside className="meeting-panel">
            <div className="meeting-panel__tabs">
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  className={`meeting-panel__tab${activeTab === tab.id ? ' is-active' : ''}`}
                  onClick={() => setActiveTab(tab.id)}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {activeTab === 'subtitle' && (
              <div className="tab-panel">
                <p className="tab-panel__label">번역 언어</p>
                <div className="lang-options">
                  {translationLanguages.map((lang) => (
                    <button
                      key={lang}
                      type="button"
                      className={`lang-btn${selectedLang === lang ? ' is-selected' : ''}`}
                      onClick={() => setSelectedLang(lang)}
                    >
                      {lang}
                    </button>
                  ))}
                </div>

                <div className="live-subtitle-row">
                  <span className="tab-panel__label">실시간 자막</span>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={liveSubtitles}
                    className={`switch${liveSubtitles ? ' is-on' : ''}`}
                    onClick={() => setLiveSubtitles((prev) => !prev)}
                  >
                    <span className="switch__knob" />
                  </button>
                </div>
              </div>
            )}

            {activeTab === 'cards' && (
              <div className="tab-panel">
                <ul className="mtg-speech-card-list">
                  {speechCards.map((card) => (
                    <li className="mtg-speech-card" key={card.id}>
                      <p className="mtg-speech-card__situation">
                        <img src={card.flag} alt="" /> {card.situation}
                      </p>
                      <p className="mtg-speech-card__korean">{card.korean}</p>
                      <p className="mtg-speech-card__translated">
                        {card.langLabel} · {card.translated}
                      </p>
                      <button
                        type="button"
                        className="mtg-speech-card__btn"
                        onClick={() => handlePasteToChat(card)}
                      >
                        💬 채팅에 붙여넣기
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {activeTab === 'participants' && (
              <div className="tab-panel">
                <ul className="participant-list">
                  {participants.map((participant) => (
                    <li className="participant-row" key={participant.id}>
                      <span
                        className="participant-row__avatar"
                        style={{ background: participant.color }}
                      >
                        {participant.isMe ? '나' : participant.name.slice(0, 1)}
                      </span>
                      <span className="participant-row__info">
                        <span className="participant-row__name">
                          {participant.name}
                          {participant.isHost && <span className="host-badge">호스트</span>}
                        </span>
                        <span className="participant-row__time">
                          {participant.tzIcon} {participant.localTime}
                        </span>
                      </span>
                      <span className={`participant-row__icon${participant.micOn ? '' : ' is-muted'}`}>
                        {participant.micOn ? '🎤' : '🔇'}
                      </span>
                      <span
                        className={`participant-row__icon${participant.cameraOn ? '' : ' is-muted'}`}
                      >
                        {participant.cameraOn ? '📷' : '🚫'}
                      </span>
                      {!participant.isMe && (
                        <button
                          type="button"
                          className="participant-row__remove"
                          aria-label={`${participant.name} 내보내기`}
                          onClick={() => handleRemoveParticipant(participant.id)}
                        >
                          ×
                        </button>
                      )}
                    </li>
                  ))}
                </ul>

                <div className="invite-row">
                  <input
                    type="text"
                    className="invite-input"
                    placeholder="이름 입력 후 초대"
                    value={inviteName}
                    onChange={(event) => setInviteName(event.target.value)}
                    onKeyDown={(event) => event.key === 'Enter' && handleInvite()}
                  />
                  <button type="button" className="invite-btn" onClick={handleInvite}>
                    초대
                  </button>
                </div>
              </div>
            )}

            {activeTab === 'chat' && (
              <div className="tab-panel tab-panel--chat">
                <ul className="chat-list" ref={chatLogRef}>
                  {chatMessages.map((message) => (
                    <li className="chat-message" key={message.id}>
                      <span className="chat-message__sender">{message.sender}</span> ·{' '}
                      <span>{message.text}</span>
                    </li>
                  ))}
                </ul>

                <form className="chat-composer" onSubmit={handleSendMessage}>
                  <input
                    type="text"
                    placeholder="메시지 입력..."
                    value={chatDraft}
                    onChange={(event) => setChatDraft(event.target.value)}
                  />
                  <button type="submit">전송</button>
                </form>
              </div>
            )}
          </aside>
        ) : (
          <aside className="waiting-card">
            <h2 className="waiting-card__title">{MEETING_TITLE}</h2>
            <p className="waiting-card__subtitle">참가 예정자 {waitingList.length}명이 이미 대기 중이에요</p>
            <ul className="waiting-card__list">
              {waitingList.map((person) => (
                <li key={person.name}>
                  <span className="waiting-card__name">{person.name}</span>
                  <span className="waiting-card__meta">
                    · {person.tzIcon} {person.localTime}
                  </span>
                </li>
              ))}
            </ul>
          </aside>
        )}
      </div>

      <div className={`meeting-toast${toast ? ' meeting-toast--visible' : ''}`} role="status">
        {toast}
      </div>
    </section>
  )
}

export default MeetingPage
