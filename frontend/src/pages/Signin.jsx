import { useState } from 'react'
import { Eye, EyeOff, Mail, Lock, Stethoscope, ArrowRight } from 'lucide-react'
import './Signin.css'

function Signin() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [remember, setRemember] = useState(false)

  const handleSubmit = (event) => {
    event.preventDefault()
  }

  return (
    <div className="signin-page">
      <div className="signin-brand">
        <div className="signin-brand-content">
          <div className="signin-logo">
            <Stethoscope size={22} />
          </div>
          <h1 className="signin-brand-title">Clinera</h1>
          <p className="signin-brand-subtitle">
            AI-assisted clinical documentation that keeps you focused on the patient,
            not the paperwork.
          </p>
        </div>
      </div>

      <div className="signin-panel">
        <form className="signin-card" onSubmit={handleSubmit}>
          <h2 className="signin-title">Welcome back</h2>
          <p className="signin-subtitle">Sign in to continue to your dashboard</p>

          <label className="signin-field">
            <span className="signin-label">Email</span>
            <span className="signin-input-wrap">
              <Mail size={16} className="signin-input-icon" />
              <input
                type="email"
                className="signin-input"
                placeholder="you@clinic.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="email"
                required
              />
            </span>
          </label>

          <label className="signin-field">
            <span className="signin-label">Password</span>
            <span className="signin-input-wrap">
              <Lock size={16} className="signin-input-icon" />
              <input
                type={showPassword ? 'text' : 'password'}
                className="signin-input"
                placeholder="Enter your password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                className="signin-input-toggle"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                onClick={() => setShowPassword((value) => !value)}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </span>
          </label>

          <div className="signin-row">
            <label className="signin-checkbox">
              <input
                type="checkbox"
                checked={remember}
                onChange={(event) => setRemember(event.target.checked)}
              />
              Remember me
            </label>
            <a href="#" className="signin-forgot">Forgot password?</a>
          </div>

          <button type="submit" className="signin-submit">
            Sign in
            <ArrowRight size={16} />
          </button>

          <p className="signin-footer">
            Don't have an account? <a href="#">Request access</a>
          </p>
        </form>
      </div>
    </div>
  )
}

export default Signin
