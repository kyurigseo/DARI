import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getSpeechCards } from '../../api/meetings'
import { useMeetingRoom } from './useMeetingRoom'
import germanFlag from '../../assets/img/flags/de.svg'
import japaneseFlag from '../../assets/img/flags/jp.svg'
import koreanFlag from '../../assets/img/flags/kr.svg'
import chineseFlag from '../../assets/img/flags/cn.svg'
import usFlag from '../../assets/img/flags/us.svg'
import './MeetingPage.css'

const TABS = [
  { id: 'subtitle', label: '자막·번역' },
  { id: 'cards', label: '발언카드' },
  { id: 'participants', label: '참가자' },
  { id: 'chat', label: '채팅' },
]

// 프론트 언어 선택지 <-> 백엔드(DeepL 등) 언어 코드 매핑
const LANGUAGE_OPTIONS = [
  { label: '한국어', code: 'KO', flag: koreanFlag },
  { label: 'English', code: 'EN-US', flag: usFlag },
  { label: '日本語', code: 'JA', flag: japaneseFlag },
  { label: '中文', code: 'ZH', flag: chineseFlag },
  { label: 'Deutsch', code: 'DE', flag: germanFlag },
]

const LANG_META_BY_CODE = LANGUAGE_OPTIONS.reduce((acc, item) => {
  acc[item.code] = item
  acc[item.code.split('-')[0]] = item
  return acc
}, {})

const formatElapsed = (totalSeconds) => {
  const minutes = Math.floor(totalSeconds / 60)
    .toString()
    .padStart(2, '0')
  const seconds = (totalSeconds % 60).toString().padStart(2, '0')
  return `${minutes}:${seconds}`
}

function VideoTile({ participant }) {
  const videoRef = useRef(null)

  useEffect(() => {
    if (videoRef.current && participant.stream) {
      videoRef.current.srcObject = participant.stream
    }
  }, [participant.stream])

  const showVideo = participant.cameraOn && participant.stream

  return (
    <div className={`video-tile${participant.speaking ? ' video-tile--speaking' : ''}`}>
      {showVideo && (
        <video
          ref={videoRef}
          className="video-tile__video"
          autoPlay
          playsInline
          muted={participant.isMe}
        />
      )}
      {!showVideo && (
        <span className="video-tile__avatar" style={{ background: participant.color }}>
          {participant.isMe ? '나' : participant.name?.slice(0, 1)}
        </span>
      )}
      <span className="video-tile__footer">
        <span className="video-tile__name">{participant.isMe ? '나' : participant.name}</span>
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
  )
}

function MeetingPage() {
  const { meetingId: roomCode } = useParams()
  const navigate = useNavigate()

  const {
    me,
    meetingInfo,
    prejoinError,
    joined,
    connecting,
    micOn,
    cameraOn,
    isScreenSharing,
    participants,
    captions,
    chatMessages,
    toast,
    join,
    leave,
    toggleMic,
    toggleCamera,
    toggleScreenShare,
    sendChat,
    invite,
    kick,
    endMeeting,
  } = useMeetingRoom(roomCode)

  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [activeTab, setActiveTab] = useState('subtitle')
  const [selectedLang, setSelectedLang] = useState('한국어')
  const [liveSubtitles, setLiveSubtitles] = useState(true)
  const [chatDraft, setChatDraft] = useState('')
  const [inviteName, setInviteName] = useState('')
  const [speechCards, setSpeechCards] = useState([])

  const chatLogRef = useRef(null)

  const meetingTitle = meetingInfo?.title || (roomCode ? `회의 ${roomCode}` : '회의')
  const isHost = Boolean(me && meetingInfo?.host_id && String(me.id) === String(meetingInfo.host_id))

  useEffect(() => {
    if (!joined) {
      setElapsedSeconds(0)
      return undefined
    }
    const timer = setInterval(() => setElapsedSeconds((prev) => prev + 1), 1000)
    return () => clearInterval(timer)
  }, [joined])

  useEffect(() => {
    getSpeechCards()
      .then(setSpeechCards)
      .catch(() => setSpeechCards([]))
  }, [])

  useEffect(() => {
    if (chatLogRef.current) {
      chatLogRef.current.scrollTop = chatLogRef.current.scrollHeight
    }
  }, [chatMessages])

  const handleSendMessage = (event) => {
    event.preventDefault()
    const trimmed = chatDraft.trim()
    if (!trimmed) return
    sendChat(trimmed)
    setChatDraft('')
  }

  const handlePasteToChat = (card) => {
    setChatDraft(card.korean_script)
    setActiveTab('chat')
  }

  const handleInvite = () => {
    const trimmed = inviteName.trim()
    if (!trimmed) return
    invite(trimmed)
    setInviteName('')
  }

  const handleEndMeeting = async () => {
    if (await endMeeting()) {
      navigate(`/summary/${roomCode}`)
    }
  }

  const selectedLangCode = LANGUAGE_OPTIONS.find((l) => l.label === selectedLang)?.code || 'KO'
  const latestCaption = captions[captions.length - 1]
  const latestTranslation =
    latestCaption?.translations?.[selectedLangCode] ??
    latestCaption?.translations?.[selectedLangCode.split('-')[0]]

  const waitingList = (meetingInfo?.participants || []).map((p) => ({
    name: p.username,
    tzIcon: '🌐',
    localTime: '--:--',
  }))

  return (
    <section className="meeting-page">
      <header className="meeting-page__heading">
        <h1>실시간 회의 — {meetingTitle}</h1>
        <p>DARI 안에서 바로 화상회의를 진행해요. 참가자 초대·내보내기도 여기서 할 수 있어요</p>
      </header>

      {prejoinError && <p className="meeting-page__error">{prejoinError}</p>}

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
                <VideoTile participant={participant} key={participant.id} />
              ))}
            </div>

            {liveSubtitles && latestCaption && (
              <div className="caption-bar">
                <p className="caption-bar__original">
                  원문 · {latestCaption.speakerName} · &quot;{latestCaption.original}&quot;
                </p>
                <p className="caption-bar__translated">
                  번역 · &quot;{latestTranslation ?? latestCaption.original}&quot;
                </p>
              </div>
            )}

            <div className="call-toolbar">
              <button type="button" className="toolbar-btn" onClick={toggleMic}>
                🎤 {micOn ? '음소거' : '음소거 해제'}
              </button>
              <button type="button" className="toolbar-btn" onClick={toggleCamera}>
                📷 카메라 {cameraOn ? '끄기' : '켜기'}
              </button>
              <button
                type="button"
                className={`toolbar-btn${isScreenSharing ? ' is-active' : ''}`}
                aria-pressed={isScreenSharing}
                onClick={toggleScreenShare}
              >
                🖥️ {isScreenSharing ? '공유 중지' : '화면공유'}
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
              <button type="button" className="toolbar-btn toolbar-btn--danger" onClick={leave}>
                📞 나가기
              </button>
              {isHost && (
                <button type="button" className="toolbar-btn toolbar-btn--danger" onClick={handleEndMeeting}>
                  ⏹️ 회의 종료
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="call-stage call-stage--prejoin">
            <div className="prejoin-preview">
              <span className="prejoin-preview__avatar">{me?.username?.slice(0, 1) || '나'}</span>
              <span className="prejoin-preview__label">
                나{micOn ? '🎤' : '🔇'}{cameraOn ? '📷' : '🚫'}
              </span>
            </div>

            <div className="prejoin-controls">
              <button
                type="button"
                className={`toggle-btn${micOn ? ' is-on' : ''}`}
                onClick={toggleMic}
              >
                🎤 마이크 {micOn ? '켜짐' : '꺼짐'}
              </button>
              <button
                type="button"
                className={`toggle-btn${cameraOn ? ' is-on' : ''}`}
                onClick={toggleCamera}
              >
                📷 카메라 {cameraOn ? '켜짐' : '꺼짐'}
              </button>
            </div>

            <button
              type="button"
              className="join-btn"
              onClick={join}
              disabled={connecting || !roomCode || !me}
            >
              {connecting ? '연결 중...' : '회의 참가하기 →'}
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
                  {LANGUAGE_OPTIONS.map((lang) => (
                    <button
                      key={lang.code}
                      type="button"
                      className={`lang-btn${selectedLang === lang.label ? ' is-selected' : ''}`}
                      onClick={() => setSelectedLang(lang.label)}
                    >
                      {lang.label}
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

                <ul className="caption-history">
                  {captions
                    .slice()
                    .reverse()
                    .map((caption) => {
                      const translated =
                        caption.translations?.[selectedLangCode] ??
                        caption.translations?.[selectedLangCode.split('-')[0]] ??
                        caption.original
                      return (
                        <li key={caption.id} className="caption-history__item">
                          <strong>{caption.speakerName}</strong>: {translated}
                        </li>
                      )
                    })}
                </ul>
              </div>
            )}

            {activeTab === 'cards' && (
              <div className="tab-panel">
                <ul className="mtg-speech-card-list">
                  {speechCards.length === 0 && (
                    <p className="tab-panel__empty">저장된 발언카드가 없어요. 리허설에서 만들어보세요!</p>
                  )}
                  {speechCards.map((card) => {
                    const meta = LANG_META_BY_CODE[card.target_lang] || LANG_META_BY_CODE.EN
                    return (
                      <li className="mtg-speech-card" key={card.id}>
                        <p className="mtg-speech-card__situation">
                          <img src={meta.flag} alt="" /> {card.situation}
                        </p>
                        <p className="mtg-speech-card__korean">{card.korean_script}</p>
                        <p className="mtg-speech-card__translated">
                          {meta.label} · {card.translated_script}
                        </p>
                        <button
                          type="button"
                          className="mtg-speech-card__btn"
                          onClick={() => handlePasteToChat(card)}
                        >
                          💬 채팅에 붙여넣기
                        </button>
                      </li>
                    )
                  })}
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
                        {participant.isMe ? '나' : participant.name?.slice(0, 1)}
                      </span>
                      <span className="participant-row__info">
                        <span className="participant-row__name">
                          {participant.isMe ? '나' : participant.name}
                          {participant.isHost && <span className="host-badge">호스트</span>}
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
                      {isHost && !participant.isMe && (
                        <button
                          type="button"
                          className="participant-row__remove"
                          aria-label={`${participant.name} 내보내기`}
                          onClick={() => kick(participant.id)}
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
                    placeholder="아이디 입력 후 초대"
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
            <h2 className="waiting-card__title">{meetingTitle}</h2>
            <p className="waiting-card__subtitle">참가 예정자 {waitingList.length}명이 이미 대기 중이에요</p>
            <ul className="waiting-card__list">
              {waitingList.map((person) => (
                <li key={person.name}>
                  <span className="waiting-card__name">{person.name}</span>
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
