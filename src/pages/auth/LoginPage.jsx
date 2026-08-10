import { useState } from 'react'
import { Link } from 'react-router-dom'
import dariLogo from '../../assets/img/logo/dari_logo.svg'
import './AuthPage.css'

function LoginPage() {
  const [form, setForm] = useState({ username: '', password: '' })
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

    if (!form.password) {
      nextErrors.password = '비밀번호를 입력해주세요.'
    }

    setErrors(nextErrors)

    if (Object.keys(nextErrors).length === 0) {
      // API 명세 확정 후 로그인 요청을 연결합니다.
    }
  }

  return (
    <main className="auth-page">
      <div className="auth-page__surface">
        <section className="auth-card auth-card--login" aria-labelledby="login-title">
          <img className="auth-card__logo" src={dariLogo} alt="DARI" />

          <div className="auth-card__heading">
            <h1 id="login-title">로그인</h1>
            <p>다시 오신 걸 환영해요</p>
          </div>

          <form className="auth-form" onSubmit={handleSubmit} noValidate>
            <div className="auth-field">
              <label htmlFor="login-username">아이디</label>
              <input
                id="login-username"
                name="username"
                type="text"
                value={form.username}
                onChange={handleChange}
                placeholder="아이디를 입력하세요"
                autoComplete="username"
                aria-invalid={Boolean(errors.username)}
                aria-describedby={errors.username ? 'login-username-error' : undefined}
              />
              {errors.username && (
                <p className="auth-field__error" id="login-username-error">
                  {errors.username}
                </p>
              )}
            </div>

            <div className="auth-field">
              <label htmlFor="login-password">비밀번호</label>
              <input
                id="login-password"
                name="password"
                type="password"
                value={form.password}
                onChange={handleChange}
                placeholder="비밀번호를 입력하세요"
                autoComplete="current-password"
                aria-invalid={Boolean(errors.password)}
                aria-describedby={errors.password ? 'login-password-error' : undefined}
              />
              {errors.password && (
                <p className="auth-field__error" id="login-password-error">
                  {errors.password}
                </p>
              )}
            </div>

            <button className="auth-form__submit" type="submit">
              로그인
            </button>
          </form>

          <p className="auth-card__switch">
            아직 계정이 없으신가요? <Link to="/signup">회원가입</Link>
          </p>
        </section>
      </div>
    </main>
  )
}

export default LoginPage
