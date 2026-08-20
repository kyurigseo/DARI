import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import dariLogo from '../../assets/img/logo/dari_logo.svg'
import { signup, login } from '../../api/auth'
import './AuthPage.css'

const countryOptions = [
  { value: 'KR', label: '대한민국' },
  { value: 'US', label: '미국' },
  { value: 'DE', label: '독일' },
  { value: 'JP', label: '일본' },
  { value: 'CN', label: '중국' },
  { value: 'OTHER', label: '기타' },
]

const roleOptions = [
  { value: 'STUDENT', label: '학생' },
  { value: 'STAFF', label: '사원 · 팀원' },
  { value: 'MANAGER', label: '팀장 · 매니저' },
  { value: 'EXECUTIVE', label: '임원 · C-level' },
  { value: 'FREELANCER', label: '프리랜서' },
  { value: 'FOUNDER', label: '창업가 · 대표' },
  { value: 'OTHER', label: '기타' },
]

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function SignupPage() {
  const navigate = useNavigate()

  const [form, setForm] = useState({
    username: '',
    email: '',
    password: '',
    country: 'KR',
    role: 'STUDENT',
  })

  const [errors, setErrors] = useState({})
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleChange = (event) => {
    const { name, value } = event.target

    setForm((currentForm) => ({
      ...currentForm,
      [name]: value,
    }))

    setErrors((currentErrors) => ({
      ...currentErrors,
      [name]: '',
    }))
  }

  const handleSubmit = async (event) => {
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
      setIsSubmitting(true)

      try {
        await signup(form)

        await login({
          username: form.username,
          password: form.password,
        })

        navigate('/')
      } catch (error) {
        const serverErrors = error.response?.data

        if (serverErrors && typeof serverErrors === 'object') {
          const mapped = {}

          for (const key of Object.keys(serverErrors)) {
            mapped[key] = Array.isArray(serverErrors[key])
              ? serverErrors[key][0]
              : String(serverErrors[key])
          }

          setErrors(mapped)
        } else {
          setErrors({
            username: '회원가입에 실패했습니다. 잠시 후 다시 시도해주세요.',
          })
        }
      } finally {
        setIsSubmitting(false)
      }
    }
  }

  return (
    <main className="auth-page">
      <div className="auth-page__surface auth-page__surface--signup">
        <section
          className="auth-card auth-card--signup"
          aria-labelledby="signup-title"
        >
          <img
            className="auth-card__logo"
            src={dariLogo}
            alt="DARI"
          />

          <div className="auth-card__heading">
            <h1 id="signup-title">회원가입</h1>
            <p>몇 가지 정보만 알려주시면 바로 시작할 수 있어요</p>
          </div>

          <form
            className="auth-form"
            onSubmit={handleSubmit}
            noValidate
          >
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
                aria-describedby={
                  errors.username
                    ? 'signup-username-error'
                    : undefined
                }
              />

              {errors.username && (
                <p
                  className="auth-field__error"
                  id="signup-username-error"
                >
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
                aria-describedby={
                  errors.email
                    ? 'signup-email-error'
                    : undefined
                }
              />

              {errors.email && (
                <p
                  className="auth-field__error"
                  id="signup-email-error"
                >
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
                aria-describedby={
                  errors.password
                    ? 'signup-password-error'
                    : undefined
                }
              />

              {errors.password && (
                <p
                  className="auth-field__error"
                  id="signup-password-error"
                >
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
                aria-describedby={
                  errors.country
                    ? 'signup-country-error'
                    : undefined
                }
              >
                {countryOptions.map((country) => (
                  <option
                    value={country.value}
                    key={country.value}
                  >
                    {country.label}
                  </option>
                ))}
              </select>

              {errors.country && (
                <p
                  className="auth-field__error"
                  id="signup-country-error"
                >
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
                aria-describedby={
                  errors.role
                    ? 'signup-role-error'
                    : undefined
                }
              >
                {roleOptions.map((role) => (
                  <option
                    value={role.value}
                    key={role.value}
                  >
                    {role.label}
                  </option>
                ))}
              </select>

              {errors.role && (
                <p
                  className="auth-field__error"
                  id="signup-role-error"
                >
                  {errors.role}
                </p>
              )}
            </div>

            <button
              className="auth-form__submit"
              type="submit"
              disabled={isSubmitting}
            >
              {isSubmitting ? '가입 중...' : '가입하기'}
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