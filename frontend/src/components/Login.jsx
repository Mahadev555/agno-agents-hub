import { useState } from 'react'
import { LogIn, UserPlus } from 'lucide-react'
import { authService } from '../services/api'

/**
 * Sign-in / sign-up gate.
 *
 * The API requires a bearer token on every endpoint, so nothing in the app is
 * reachable until this succeeds.
 */
const Login = ({ onAuthenticated, notice }) => {
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const isRegister = mode === 'register'

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (!email.trim() || !password) return

    setBusy(true)
    setError(null)
    try {
      const user = isRegister
        ? await authService.register(email.trim(), password, displayName.trim())
        : await authService.login(email.trim(), password)
      onAuthenticated(user)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-screen">
      <section
        className="card p-8 w-full max-w-md space-y-6"
      >
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Agno Hub</h1>
          <p className="text-slate-600 mt-1">
            {isRegister ? 'Create an account to get started' : 'Sign in to continue'}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {notice && (
            <div className="feedback-warning" role="status">
              {notice}
            </div>
          )}
          <div>
            <label htmlFor="login-email" className="block text-sm font-medium text-slate-700 mb-1">Email</label>
            <input
              id="login-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input-primary w-full"
              autoComplete="email"
              required
              disabled={busy}
            />
          </div>

          {isRegister && (
            <div>
              <label htmlFor="display-name" className="block text-sm font-medium text-slate-700 mb-1">
                Display name <span className="text-slate-400">(optional)</span>
              </label>
              <input
                id="display-name"
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="input-primary w-full"
                disabled={busy}
              />
            </div>
          )}

          <div>
            <label htmlFor="login-password" className="block text-sm font-medium text-slate-700 mb-1">Password</label>
            <input
              id="login-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input-primary w-full"
              autoComplete={isRegister ? 'new-password' : 'current-password'}
              required
              minLength={isRegister ? 10 : undefined}
              disabled={busy}
            />
            {isRegister && (
              <p className="text-xs text-slate-500 mt-1">
                At least 10 characters. A long passphrase beats a short complex one.
              </p>
            )}
          </div>

          {error && (
            <div className="feedback-error" role="alert">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={busy || !email.trim() || !password}
            className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {isRegister
              ? <UserPlus size={16} strokeWidth={1.5} aria-hidden="true" />
              : <LogIn size={16} strokeWidth={1.5} aria-hidden="true" />}
            {busy ? 'Please wait...' : isRegister ? 'Create account' : 'Sign in'}
          </button>
        </form>

        <button
          type="button"
          onClick={() => {
            setMode(isRegister ? 'login' : 'register')
            setError(null)
          }}
          className="w-full text-center text-sm text-brand-text hover:underline"
        >
          {isRegister ? 'Already have an account? Sign in' : 'Need an account? Register'}
        </button>
      </section>
    </div>
  )
}

export default Login
