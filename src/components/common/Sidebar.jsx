import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import dariLogo from '../../assets/img/logo/dari_logo.svg'
import { getCardCount } from '../../api/cards'
import './Sidebar.css'

const navigationItems = [
  { label: '홈', icon: '🏠', to: '/', end: true },
  { label: 'AI 리허설', icon: '🎭', to: '/rehearsal' },
  { label: '발언 카드함', icon: '🗂️', to: '/cards' },
  { label: '실시간 회의', icon: '🎥', to: '/meeting/m1' },
  { label: '시차 트래커', icon: '🌓', to: '/tracker' },
  { label: '회의 요약', icon: '📝', to: '/summary/m1' },
  { label: '마이페이지', icon: '👤', to: '/mypage' },
]

function Sidebar({ isOpen, onClose }) {
  const [cardCount, setCardCount] = useState(0)

  useEffect(() => {
    const fetchCardCount = async () => {
      try {
        const data = await getCardCount()
        setCardCount(data.count ?? 0)
      } catch (error) {
        console.error('발언 카드 개수를 불러오지 못했습니다.', error)
        setCardCount(0)
      }
    }

    fetchCardCount()
  }, [])

  return (
    <>
      <button
        className={`sidebar-backdrop${isOpen ? ' sidebar-backdrop--open' : ''}`}
        type="button"
        aria-label="메뉴 닫기"
        onClick={onClose}
      />

      <aside
        className={`sidebar${isOpen ? ' sidebar--open' : ''}`}
        aria-hidden={!isOpen}
      >
        <div className="sidebar__header">
          <div className="sidebar__brand">
            <img className="sidebar__logo" src={dariLogo} alt="DARI" />
          </div>

          <button
            className="sidebar__close"
            type="button"
            onClick={onClose}
            aria-label="메뉴 닫기"
          >
            <span aria-hidden="true">✕</span>
          </button>
        </div>

        <nav className="sidebar__nav" aria-label="주요 메뉴">
          {navigationItems.map((item) => (
            <NavLink
              key={item.label}
              className={({ isActive }) =>
                `sidebar__item${isActive ? ' sidebar__item--active' : ''}`
              }
              to={item.to}
              end={item.end}
              onClick={onClose}
            >
              <span className="sidebar__icon" aria-hidden="true">
                {item.icon}
              </span>

              <span>{item.label}</span>

              {item.label === '발언 카드함' && cardCount > 0 && (
                <span className="sidebar__badge">{cardCount}</span>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar__footer">DARI · 프로토타입 v0.7</div>
      </aside>
    </>
  )
}

export default Sidebar