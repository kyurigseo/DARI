import { Link } from 'react-router-dom'
import dariLogo from '../../assets/img/logo/dari_logo.svg'
import './Header.css'

function Header({ onMenuClick }) {
  return (
    <header className="header">
      <div className="header__left">
        <button
          className="header__menu-button"
          type="button"
          onClick={onMenuClick}
          aria-label="메뉴 열기"
        >
          <span className="header__menu-icon" aria-hidden="true">
            <span />
            <span />
            <span />
          </span>
        </button>
        <Link className="header__brand" to="/">
          <img className="header__logo" src={dariLogo} alt="DARI" />
        </Link>
      </div>

      <div className="header__right">
        <Link className="header__meeting" to="/meeting/m1">
          <span aria-hidden="true">📅</span>
          <span>14:00 · Acme Corp 협상</span>
        </Link>
        <Link className="header__profile" to="/mypage" aria-label="마이페이지">
          김
        </Link>
      </div>
    </header>
  )
}

export default Header
