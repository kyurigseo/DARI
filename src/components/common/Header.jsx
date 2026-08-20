import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getMyPage } from '../../api/auth'
import dariLogo from '../../assets/img/logo/dari_logo.svg'
import NotificationBell from './NotificationBell'
import './Header.css'

function Header({ onMenuClick }) {
  const [profile, setProfile] = useState(null)

  useEffect(() => {
    let isMounted = true

    getMyPage()
      .then((data) => {
        if (!isMounted) return
        setProfile({ name: data.name, profileImage: data.profile_image })
      })
      .catch(() => {
        // 헤더는 항상 떠 있어야 하므로 조회 실패 시에도 조용히 기본값(이니셜 없음)으로 둔다.
      })

    return () => {
      isMounted = false
    }
  }, [])

  const initial = profile?.name?.trim()?.slice(0, 1) || ''

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
        {/* <Link className="header__meeting" to="/">
          <span aria-hidden="true">📅</span>
          <span>14:00 · Acme Corp 협상</span>
        </Link> */}
        <NotificationBell />
        <Link className="header__profile" to="/mypage" aria-label="마이페이지">
          {profile?.profileImage ? (
            <img className="header__profile-image" src={profile.profileImage} alt="" />
          ) : (
            initial
          )}
        </Link>
      </div>
    </header>
  )
}

export default Header