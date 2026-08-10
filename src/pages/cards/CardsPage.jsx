import { useEffect, useRef, useState } from 'react'
import { initialCards } from './cardsMockData'
import './CardsPage.css'

function CardsPage() {
  const [cards, setCards] = useState(initialCards)
  const [selectedCard, setSelectedCard] = useState(null)
  const [toast, setToast] = useState('')
  const toastTimerRef = useRef(null)

  const showToast = (message) => {
    setToast(message)

    if (toastTimerRef.current) {
      clearTimeout(toastTimerRef.current)
    }

    toastTimerRef.current = setTimeout(() => {
      setToast('')
    }, 2500)
  }

  const copyText = async (text) => {
    try {
      await navigator.clipboard.writeText(text)
      showToast('클립보드에 복사했어요 📋')
    } catch {
      // Clipboard 권한이 없거나 복사에 실패하면 성공 Toast를 표시하지 않습니다.
    }
  }

  const deleteCard = (cardId) => {
    setCards((currentCards) => currentCards.filter((card) => card.id !== cardId))
    setSelectedCard((currentCard) => (currentCard?.id === cardId ? null : currentCard))
    showToast('카드를 삭제했어요 🗑️')

    // TODO: 카드 API 명세 확정 후 서버 삭제 요청을 연결합니다.
  }

  useEffect(() => {
    if (!selectedCard) return undefined

    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        setSelectedCard(null)
      }
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [selectedCard])

  useEffect(
    () => () => {
      if (toastTimerRef.current) {
        clearTimeout(toastTimerRef.current)
      }
    },
    [],
  )

  return (
    <section className="cards-page">
      <header className="cards-page__heading">
        <h1>발언 카드함</h1>
        <p>어떤 상황에서 어떤 말을 해야 하는지, 상대방 언어 번역까지 함께 확인하세요</p>
      </header>

      {cards.length > 0 ? (
        <div className="speech-card-grid">
          {cards.map((card) => (
            <article className={`speech-card speech-card--${card.tone}`} key={card.id}>
              <div className="speech-card__accent" />
              <div className="speech-card__body">
                <div className="speech-card__tags">
                  <span className={`speech-card__persona speech-card__persona--${card.tone}`}>
                    <img src={card.flag} alt="" />
                    {card.persona}
                  </span>
                  <span className="speech-card__situation">🗣️ {card.situation}</span>
                </div>

                <div className="speech-card__sentence">
                  <span className="speech-card__language speech-card__language--ko">KO</span>
                  <p>{card.korean}</p>
                  <button
                    type="button"
                    aria-label={`${card.persona} 한국어 문장 복사`}
                    onClick={() => copyText(card.korean)}
                  >
                    📋
                  </button>
                </div>

                <div className="speech-card__sentence">
                  <span className="speech-card__language">{card.language}</span>
                  <p>{card.translation}</p>
                  <button
                    type="button"
                    aria-label={`${card.persona} 번역 문장 복사`}
                    onClick={() => copyText(card.translation)}
                  >
                    📋
                  </button>
                </div>

                <footer className="speech-card__footer">
                  <span>{card.savedAt}</span>
                  <div className="speech-card__actions">
                    <button
                      type="button"
                      aria-label={`${card.persona} 카드 상세보기`}
                      onClick={() => setSelectedCard(card)}
                    >
                      👁️
                    </button>
                    <button
                      type="button"
                      aria-label={`${card.persona} 카드 삭제`}
                      onClick={() => deleteCard(card.id)}
                    >
                      🗑️
                    </button>
                  </div>
                </footer>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="cards-empty">
          <p>아직 저장된 발언 카드가 없어요.</p>
          <span>AI 리허설에서 유용한 표현을 저장해보세요.</span>
        </div>
      )}

      {selectedCard && (
        <div className="card-modal-backdrop" onMouseDown={() => setSelectedCard(null)}>
          <section
            className="card-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="card-modal-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <h2 className="card-modal__persona" id="card-modal-title">
              <img src={selectedCard.flag} alt="" />
              {selectedCard.persona} · {selectedCard.savedAt}
            </h2>
            <p className="card-modal__situation">🗣️ {selectedCard.situation}</p>
            <p className="card-modal__korean">
              <img src={selectedCard.koreanFlag} alt="대한민국 국기" />
              {selectedCard.korean}
            </p>
            <p className="card-modal__translation">
              {selectedCard.languageName} · {selectedCard.translation}
            </p>
            <div className="card-modal__actions">
              <button
                className="card-modal__copy"
                type="button"
                onClick={() => copyText(selectedCard.translation)}
              >
                📋 번역 복사
              </button>
              <button className="card-modal__close" type="button" onClick={() => setSelectedCard(null)}>
                닫기
              </button>
            </div>
          </section>
        </div>
      )}

      <div className={`cards-toast${toast ? ' cards-toast--visible' : ''}`} role="status">
        {toast}
      </div>
    </section>
  )
}

export default CardsPage
