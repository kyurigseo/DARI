import { useState } from 'react'
import { Link } from 'react-router-dom'
import dariLogo from '../../assets/img/logo/dari_logo.svg'
import './AuthPage.css'

const countryOptions = ['대한민국', '미국', '독일', '일본', '중국', '기타']

const roleOptions = [
  '학생',
  '사원 · 팀원',
  '팀장 · 매니저',
  '임원 · C-level',
  '프리랜서',
  '창업가 · 대표',
  '기타',
]

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function SignupPage() {
  const [form, setForm] = useState({
    username: '',
    email: '',
    password: '',
    country: '대한민국',
    role: '학생',
  })
  const [errors, setErrors] = useState({})

  const handleChange = (event) => {
    const { name, value } = event.target

    setForm((currentForm) => ({ ...currentForm, [name]: value }))
    setErrors((currentErrors) => ({ ...currentErrors, [name]: '' }))
  }

  const handleSubmit = (event) => {
    event.preventDefault()

    const nextErrors = {}

    if (!form.username.trim()) {
      nextErrors.username = '아이디를 입력해주세요.'
    }

    if (!form.email.trim()) {
      nextErrors.email = '이메일을 입력해주세요.'
    } else if (!emailPattern.test(form.email.trim())) {
      nextErrors.email = '올바른 이메일 형식을 입력해주세요.'
    }

    if (!form.password) {
      nextErrors.password = '비밀번호를 입력해주세요.'
    }

    if (!form.country) {
      nextErrors.country = '국가를 선택해주세요.'
    }

    if (!form.role) {
      nextErrors.role = '역할을 선택해주세요.'
    }

    setErrors(nextErrors)

    if (Object.keys(nextErrors).length === 0) {
      // API 명세 확정 후 회원가입 요청을 연결합니다.
    }
  }

  return (
    <main className="auth-page">
      <div className="auth-page__surface auth-page__surface--signup">
        <section className="auth-card auth-card--signup" aria-labelledby="signup-title">
          <img className="auth-card__logo" src={dariLogo} alt="DARI" />

          <div className="auth-card__heading">
            <h1 id="signup-title">회원가입</h1>
            <p>몇 가지 정보만 알려주시면 바로 시작할 수 있어요</p>
          </div>

          <form className="auth-form" onSubmit={handleSubmit} noValidate>
            <div className="auth-field">
              <label htmlFor="signup-username">아이디</label>
              <input
                id="signup-username"
                name="username"
                type="text"
                value={form.username}
                onChange={handleChange}
                placeholder="사용하실 아이디"
                autoComplete="username"
                aria-invalid={Boolean(errors.username)}
                aria-describedby={errors.username ? 'signup-username-error' : undefined}
              />
              {errors.username && (
                <p className="auth-field__error" id="signup-username-error">
                  {errors.username}
                </p>
              )}
            </div>

            <div className="auth-field">
              <label htmlFor="signup-email">이메일</label>
              <input
                id="signup-email"
                name="email"
                type="email"
                value={form.email}
                onChange={handleChange}
                placeholder="you@example.com"
                autoComplete="email"
                aria-invalid={Boolean(errors.email)}
                aria-describedby={errors.email ? 'signup-email-error' : undefined}
              />
              {errors.email && (
                <p className="auth-field__error" id="signup-email-error">
                  {errors.email}
                </p>
              )}
            </div>

            <div className="auth-field">
              <label htmlFor="signup-password">비밀번호</label>
              <input
                id="signup-password"
                name="password"
                type="password"
                value={form.password}
                onChange={handleChange}
                placeholder="비밀번호"
                autoComplete="new-password"
                aria-invalid={Boolean(errors.password)}
                aria-describedby={errors.password ? 'signup-password-error' : undefined}
              />
              {errors.password && (
                <p className="auth-field__error" id="signup-password-error">
                  {errors.password}
                </p>
              )}
            </div>

            <div className="auth-field">
              <label htmlFor="signup-country">국가</label>
              <select
                id="signup-country"
                name="country"
                value={form.country}
                onChange={handleChange}
                aria-invalid={Boolean(errors.country)}
                aria-describedby={errors.country ? 'signup-country-error' : undefined}
              >
                {countryOptions.map((country) => (
                  <option value={country} key={country}>
                    {country}
                  </option>
                ))}
              </select>
              {errors.country && (
                <p className="auth-field__error" id="signup-country-error">
                  {errors.country}
                </p>
              )}
            </div>

            <div className="auth-field">
              <label htmlFor="signup-role">나를 나타내는 역할</label>
              <select
                id="signup-role"
                name="role"
                value={form.role}
                onChange={handleChange}
                aria-invalid={Boolean(errors.role)}
                aria-describedby={errors.role ? 'signup-role-error' : undefined}
              >
                {roleOptions.map((role) => (
                  <option value={role} key={role}>
                    {role}
                  </option>
                ))}
              </select>
              {errors.role && (
                <p className="auth-field__error" id="signup-role-error">
                  {errors.role}
                </p>
              )}
            </div>

            <button className="auth-form__submit" type="submit">
              가입하기
            </button>
          </form>

          <p className="auth-card__switch">
            이미 계정이 있으신가요? <Link to="/login">로그인</Link>
          </p>
        </section>
      </div>
    </main>
  )
}

export default SignupPage
