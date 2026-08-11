import { useRef, useState } from 'react'
import './MyPage.css'

const AVATAR_COLORS = ['#FF9351', '#8454F6', '#20AD7A', '#4C5FD5']

const initialProfile = {
  name: '김지민',
  role: 'PM · Acme팀',
  email: 'jimin@dari.io',
  avatarColor: AVATAR_COLORS[0],
}

const stats = [
  { id: 'cards', label: '저장한 발언카드', value: 2 },
  { id: 'rehearsals', label: '완료한 리허설', value: 12 },
  { id: 'meetings', label: '참여한 회의', value: 8 },
]

function MyPage() {
  const [profile, setProfile] = useState(initialProfile)
  const [notifyEnabled, setNotifyEnabled] = useState(true)
  const [translateLang] = useState('한국어')

  // 정보 수정 모달 상태
  const [isEditOpen, setIsEditOpen] = useState(false)
  const [draft, setDraft] = useState(initialProfile)
  const [toast, setToast] = useState(null)

  const toastTimerRef = useRef(null)

  const showToast = (message) => {
    clearTimeout(toastTimerRef.current)
    setToast(message)
    toastTimerRef.current = setTimeout(() => setToast(null), 2500)
  }

  const openEditModal = () => {
    setDraft(profile)
    setIsEditOpen(true)
  }

  const closeEditModal = () => {
    setIsEditOpen(false)
  }

  const handleDraftChange = (field) => (event) => {
    setDraft((prev) => ({ ...prev, [field]: event.target.value }))
  }

  const handleChangePhoto = () => {
    setDraft((prev) => {
      const nextIndex = (AVATAR_COLORS.indexOf(prev.avatarColor) + 1) % AVATAR_COLORS.length
      return { ...prev, avatarColor: AVATAR_COLORS[nextIndex] }
    })
  }

  const handleSave = () => {
    if (!draft.name.trim() || !draft.email.trim()) return

    setProfile({
      ...draft,
      name: draft.name.trim(),
      role: draft.role.trim(),
      email: draft.email.trim(),
    })
    showToast('내 정보가 수정되었어요 ✅')
    setIsEditOpen(false)
  }

  const handleToggleNotify = () => {
    setNotifyEnabled((prev) => !prev)
  }

  const handleLogout = () => {
    showToast('로그아웃 되었어요 👋')
  }

  return (
    <section className="mypage">
      <header className="mypage__heading">
        <h1>마이페이지</h1>
        <p>내 정보와 활동 현황을 확인하세요</p>
      </header>

      <article className="profile-card">
        <div className="profile-card__avatar" style={{ background: profile.avatarColor }}>
          {profile.name.charAt(0)}
        </div>
        <div className="profile-card__info">
          <p className="profile-card__name">{profile.name}</p>
          <p className="profile-card__meta">
            {profile.role} · {profile.email}
          </p>
        </div>
        <button className="profile-card__edit" type="button" onClick={openEditModal}>
          정보 수정
        </button>
      </article>

      <div className="stats-row">
        {stats.map((stat) => (
          <div className="stat-card" key={stat.id}>
            <p className="stat-card__value">{stat.value}</p>
            <p className="stat-card__label">{stat.label}</p>
          </div>
        ))}
      </div>

      <article className="settings-card">
        <h2 className="settings-card__title">설정</h2>

        <div className="settings-row">
          <span className="settings-row__label">
            <span aria-hidden="true">🔔</span> 알림 받기
          </span>
          <button
            className={`toggle-switch${notifyEnabled ? ' toggle-switch--on' : ''}`}
            type="button"
            role="switch"
            aria-checked={notifyEnabled}
            onClick={handleToggleNotify}
          >
            <span className="toggle-switch__thumb" />
          </button>
        </div>

        <div className="settings-row">
          <span className="settings-row__label">
            <span aria-hidden="true">🌐</span> 기본 번역 언어
          </span>
          <span className="lang-pill">{translateLang}</span>
        </div>
      </article>

      <button className="logout-button" type="button" onClick={handleLogout}>
        로그아웃
      </button>

      {/* 내 정보 수정 모달 */}
      {isEditOpen && (
        <div className="mypage-modal-overlay" onClick={closeEditModal}>
          <div className="mypage-modal" onClick={(event) => event.stopPropagation()}>
            <h3 className="mypage-modal__title">내 정보 수정</h3>

            <div className="mypage-modal__avatar-row">
              <div className="mypage-modal__avatar" style={{ background: draft.avatarColor }}>
                {draft.name.charAt(0) || '?'}
              </div>
              <button className="photo-change-button" type="button" onClick={handleChangePhoto}>
                사진 변경
              </button>
            </div>

            <label className="mypage-modal__field">
              <span className="mypage-modal__field-label">이름</span>
              <input type="text" value={draft.name} onChange={handleDraftChange('name')} />
            </label>

            <label className="mypage-modal__field">
              <span className="mypage-modal__field-label">직함 · 팀</span>
              <input type="text" value={draft.role} onChange={handleDraftChange('role')} />
            </label>

            <label className="mypage-modal__field">
              <span className="mypage-modal__field-label">이메일</span>
              <input type="email" value={draft.email} onChange={handleDraftChange('email')} />
            </label>

            <button
              className="mypage-modal__save"
              type="button"
              onClick={handleSave}
              disabled={!draft.name.trim() || !draft.email.trim()}
            >
              저장하기
            </button>
          </div>
        </div>
      )}

      <div className={`mypage-toast${toast ? ' mypage-toast--visible' : ''}`} role="status">
        {toast}
      </div>
    </section>
  )
}

export default MyPage