import { useEffect, useRef, useState } from 'react'
import koreanFlag from '../../assets/img/flags/kr.svg'
import { answerExamples, personas } from './rehearsalMockData'
import './RehearsalPage.css'

const createInitialMessages = (persona) => [
  { id: `${persona.id}-initial`, sender: 'ai', text: persona.initialMessage },
]

function RehearsalPage() {
  const [selectedPersona, setSelectedPersona] = useState(personas[0].id)
  const [inputValue, setInputValue] = useState('')
  const [messages, setMessages] = useState(() => createInitialMessages(personas[0]))
  const [showFeedback, setShowFeedback] = useState(false)
  const [saved, setSaved] = useState(false)
  const [toast, setToast] = useState(false)
  const chatLogRef = useRef(null)
  const toastTimerRef = useRef(null)

  const activePersona = personas.find((persona) => persona.id === selectedPersona)

  useEffect(() => {
    const chatLog = chatLogRef.current

    if (chatLog) {
      chatLog.scrollTop = chatLog.scrollHeight
    }
  }, [messages, showFeedback])

  useEffect(
    () => () => {
      if (toastTimerRef.current) {
        clearTimeout(toastTimerRef.current)
      }
    },
    [],
  )

  const handlePersonaChange = (persona) => {
    setSelectedPersona(persona.id)
    setInputValue('')
    setMessages(createInitialMessages(persona))
    setShowFeedback(false)
    setSaved(false)
    setToast(false)

    if (toastTimerRef.current) {
      clearTimeout(toastTimerRef.current)
    }
  }

  const handleSubmit = (event) => {
    event.preventDefault()

    const message = inputValue.trim()

    if (!message) return

    const isFirstReply = !showFeedback
    const nextMessages = [
      ...messages,
      { id: `user-${Date.now()}`, sender: 'user', text: message },
    ]

    if (isFirstReply) {
      nextMessages.push({
        id: `ai-follow-up-${Date.now()}`,
        sender: 'ai',
        text: activePersona.followUpMessage,
      })
    }

    setMessages(nextMessages)
    setShowFeedback(isFirstReply || showFeedback)
    setInputValue('')

    // TODO: AI API 명세 확정 후 Mock 응답을 실제 대화 응답으로 교체합니다.
  }

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      event.currentTarget.form?.requestSubmit()
    }
  }

  const handleSaveCard = () => {
    if (saved) return

    setSaved(true)
    setToast(true)

    if (toastTimerRef.current) {
      clearTimeout(toastTimerRef.current)
    }

    toastTimerRef.current = setTimeout(() => {
      setToast(false)
    }, 2500)

    // TODO: 카드 저장 API 명세 확정 후 서버 저장 로직을 연결합니다.
  }

  return (
    <section className="rehearsal-page">
      <header className="rehearsal-page__heading">
        <h1>AI 리허설</h1>
        <p>실전처럼 대화하며 표현을 다듬어보세요. 피드백은 대화 중간중간 바로 확인할 수 있어요</p>
      </header>

      <div className="persona-list" role="group" aria-label="대화 상대 선택">
        {personas.map((persona) => {
          const isActive = persona.id === selectedPersona

          return (
            <button
              className={`persona-button${isActive ? ' persona-button--active' : ''}`}
              type="button"
              aria-pressed={isActive}
              onClick={() => handlePersonaChange(persona)}
              key={persona.id}
            >
              <img className="persona-button__flag" src={persona.flag} alt="" />
              {persona.label}
            </button>
          )
        })}
      </div>

      <div className="rehearsal-chat">
        <div className="rehearsal-chat__log" ref={chatLogRef} aria-live="polite">
          {messages.map((message, index) => (
            <div key={message.id}>
              <div className={`chat-message chat-message--${message.sender}`}>
                {message.sender === 'ai' && (
                  <span className="chat-avatar chat-avatar--ai">
                    <img src={activePersona.flag} alt={`${activePersona.label} 국기`} />
                  </span>
                )}
                <p className="chat-message__bubble">{message.text}</p>
                {message.sender === 'user' && (
                  <span className="chat-avatar chat-avatar--user" aria-label="나">
                    나
                  </span>
                )}
              </div>

              {message.sender === 'user' && showFeedback && index === 1 && (
                <article className="coach-feedback">
                  <h2>💡 AI 코치 피드백</h2>
                  <p className="coach-feedback__situation">상황 · 일정 지연 사유를 설명해야 할 때</p>
                  <p className="coach-feedback__tip">
                    더 직설적으로 바꿔볼까요? 원인 → 대안 순으로 짧게 말해보세요.
                  </p>
                  <p className="coach-feedback__recommendation">
                    <img src={koreanFlag} alt="대한민국 국기" />
                    <span>일정 지연 원인은 A이고, 대안으로 B를 제안드립니다.</span>
                  </p>
                  <p className="coach-feedback__translation">
                    Deutsch · Die Verzögerung liegt an A, als Alternative schlage ich B vor.
                  </p>
                  <button
                    className={`coach-feedback__save${saved ? ' coach-feedback__save--saved' : ''}`}
                    type="button"
                    onClick={handleSaveCard}
                    disabled={saved}
                  >
                    {saved ? '✓ 카드로 저장됨' : '🗂️ 카드로 저장'}
                  </button>
                </article>
              )}
            </div>
          ))}
        </div>

        <div className="answer-examples">
          <p>💡 AI 답변 예시 — 눌러서 입력창에 채워보세요</p>
          <div className="answer-examples__list">
            {answerExamples.map((example) => (
              <button type="button" onClick={() => setInputValue(example)} key={example}>
                {example}
              </button>
            ))}
          </div>
        </div>

        <form className="rehearsal-composer" onSubmit={handleSubmit}>
          <textarea
            aria-label="답변"
            rows="1"
            value={inputValue}
            onChange={(event) => setInputValue(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="답변을 입력해보세요"
          />
          <button type="submit">전송</button>
        </form>
      </div>

      <div className={`rehearsal-toast${toast ? ' rehearsal-toast--visible' : ''}`} role="status">
        카드함에 저장했어요 🗂️
      </div>
    </section>
  )
}

export default RehearsalPage
