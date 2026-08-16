import { useEffect, useRef, useState } from 'react'
import koreanFlag from '../../assets/img/flags/kr.svg'
import { getPersonas, startSession, sendMessage, saveFeedbackAsCard } from '../../api/rehearsal'
import { getLanguageMeta } from '../cards/languageMeta'
import './RehearsalPage.css'

function personaFlag(persona) {
  return getLanguageMeta(persona.culture_tag).flag
}

function RehearsalPage() {
  const [personas, setPersonas] = useState([])
  const [selectedPersonaId, setSelectedPersonaId] = useState(null)
  const [sessionId, setSessionId] = useState(null)
  const [inputValue, setInputValue] = useState('')
  const [messages, setMessages] = useState([])
  const [pendingFeedback, setPendingFeedback] = useState(null) // { afterMessageId, feedback }
  const [savedFeedbackIds, setSavedFeedbackIds] = useState(new Set())
  const [toast, setToast] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [isSending, setIsSending] = useState(false)
  const chatLogRef = useRef(null)
  const toastTimerRef = useRef(null)

  const activePersona = personas.find((persona) => persona.persona_id === selectedPersonaId)

  useEffect(() => {
    let isMounted = true

    getPersonas()
      .then((data) => {
        if (!isMounted) return
        setPersonas(data)
        if (data.length > 0) {
          handlePersonaChange(data[0])
        }
      })
      .catch(() => {})
      .finally(() => {
        if (isMounted) setIsLoading(false)
      })

    return () => {
      isMounted = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const chatLog = chatLogRef.current
    if (chatLog) {
      chatLog.scrollTop = chatLog.scrollHeight
    }
  }, [messages, pendingFeedback])

  useEffect(
    () => () => {
      if (toastTimerRef.current) {
        clearTimeout(toastTimerRef.current)
      }
    },
    [],
  )

  const handlePersonaChange = async (persona) => {
    setSelectedPersonaId(persona.persona_id)
    setInputValue('')
    setMessages([])
    setPendingFeedback(null)
    setSessionId(null)
    setToast(false)

    if (toastTimerRef.current) {
      clearTimeout(toastTimerRef.current)
    }

    try {
      const data = await startSession({ personaId: persona.persona_id, context: '' })
      setSessionId(data.session_id)
      setMessages([{ id: 'opening', sender: 'ai', text: data.opening_message }])
    } catch {
      setMessages([{ id: 'error', sender: 'ai', text: '세션을 시작하지 못했어요. 잠시 후 다시 시도해주세요.' }])
    }
  }

  const handleSubmit = async (event) => {
    event.preventDefault()

    const text = inputValue.trim()
    if (!text || !sessionId || isSending) return

    const userMessage = { id: `user-${Date.now()}`, sender: 'user', text }
    setMessages((current) => [...current, userMessage])
    setInputValue('')
    setIsSending(true)

    try {
      const data = await sendMessage(sessionId, text)
      setMessages((current) => [
        ...current,
        { id: data.ai_message.id, sender: 'ai', text: data.ai_message.content },
      ])
      setPendingFeedback({ afterMessageId: userMessage.id, feedback: data.feedback })
    } catch {
      setMessages((current) => [
        ...current,
        { id: `error-${Date.now()}`, sender: 'ai', text: '응답을 받지 못했어요. 다시 시도해주세요.' },
      ])
    } finally {
      setIsSending(false)
    }
  }

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      event.currentTarget.form?.requestSubmit()
    }
  }

  const handleSaveCard = async (feedbackId) => {
    if (savedFeedbackIds.has(feedbackId)) return

    try {
      await saveFeedbackAsCard(feedbackId, '')
      setSavedFeedbackIds((current) => new Set(current).add(feedbackId))
      setToast(true)

      if (toastTimerRef.current) {
        clearTimeout(toastTimerRef.current)
      }
      toastTimerRef.current = setTimeout(() => setToast(false), 2500)
    } catch {
      // 저장 실패 시 토스트를 띄우지 않고 버튼을 다시 활성 상태로 둔다.
    }
  }

  if (isLoading) {
    return (
      <section className="rehearsal-page">
        <p>불러오는 중...</p>
      </section>
    )
  }

  return (
    <section className="rehearsal-page">
      <header className="rehearsal-page__heading">
        <h1>AI 리허설</h1>
        <p>실전처럼 대화하며 표현을 다듬어보세요. 피드백은 대화 중간중간 바로 확인할 수 있어요</p>
      </header>

      <div className="persona-list" role="group" aria-label="대화 상대 선택">
        {personas.map((persona) => {
          const isActive = persona.persona_id === selectedPersonaId

          return (
            <button
              className={`persona-button${isActive ? ' persona-button--active' : ''}`}
              type="button"
              aria-pressed={isActive}
              onClick={() => handlePersonaChange(persona)}
              key={persona.persona_id}
            >
              <img className="persona-button__flag" src={personaFlag(persona)} alt="" />
              {persona.name}
            </button>
          )
        })}
      </div>

      <div className="rehearsal-chat">
        <div className="rehearsal-chat__log" ref={chatLogRef} aria-live="polite">
          {messages.map((message) => (
            <div key={message.id}>
              <div className={`chat-message chat-message--${message.sender}`}>
                {message.sender === 'ai' && activePersona && (
                  <span className="chat-avatar chat-avatar--ai">
                    <img src={personaFlag(activePersona)} alt={`${activePersona.name} 국기`} />
                  </span>
                )}
                <p className="chat-message__bubble">{message.text}</p>
                {message.sender === 'user' && (
                  <span className="chat-avatar chat-avatar--user" aria-label="나">
                    나
                  </span>
                )}
              </div>

              {message.sender === 'user' &&
                pendingFeedback &&
                pendingFeedback.afterMessageId === message.id && (
                  <article className="coach-feedback">
                    <h2>💡 AI 코치 피드백</h2>
                    <p className="coach-feedback__situation">상황 · {pendingFeedback.feedback.situation_label}</p>
                    <p className="coach-feedback__tip">{pendingFeedback.feedback.explanation}</p>
                    <p className="coach-feedback__recommendation">
                      <img src={koreanFlag} alt="대한민국 국기" />
                      <span>{pendingFeedback.feedback.suggested_text}</span>
                    </p>
                    <p className="coach-feedback__translation">
                      {getLanguageMeta(pendingFeedback.feedback.translated_language).name} ·{' '}
                      {pendingFeedback.feedback.translated_text}
                    </p>
                    <button
                      className={`coach-feedback__save${
                        savedFeedbackIds.has(pendingFeedback.feedback.feedback_id)
                          ? ' coach-feedback__save--saved'
                          : ''
                      }`}
                      type="button"
                      onClick={() => handleSaveCard(pendingFeedback.feedback.feedback_id)}
                      disabled={savedFeedbackIds.has(pendingFeedback.feedback.feedback_id)}
                    >
                      {savedFeedbackIds.has(pendingFeedback.feedback.feedback_id)
                        ? '✓ 카드로 저장됨'
                        : '🗂️ 카드로 저장'}
                    </button>
                  </article>
                )}
            </div>
          ))}
        </div>

        <form className="rehearsal-composer" onSubmit={handleSubmit}>
          <textarea
            aria-label="답변"
            rows="1"
            value={inputValue}
            onChange={(event) => setInputValue(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="답변을 입력해보세요"
            disabled={isSending}
          />
          <button type="submit" disabled={isSending}>
            {isSending ? '전송 중...' : '전송'}
          </button>
        </form>
      </div>

      <div className={`rehearsal-toast${toast ? ' rehearsal-toast--visible' : ''}`} role="status">
        카드함에 저장했어요 🗂️
      </div>
    </section>
  )
}

export default RehearsalPage
