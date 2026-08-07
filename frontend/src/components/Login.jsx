import { useState } from 'react'
import { motion } from 'framer-motion'
import { LogIn, UserPlus } from 'lucide-react'
import { authService } from '../services/api'

/**
 * Sign-in / sign-up gate.
 *
 * The API requires a bearer token on every endpoint, so nothing in the app is
 * reachable until this succeeds.
 */
const Login = ({ onAuthenticated }) => {
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
    <div className="min-h-screen flex items-center justify-center p-6 bg-slate-50">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="card p-8 w-full max-w-md space-y-6"
      >
        <div>
          <h1 className="text-3xl font-bold gradient-text">Agno Hub</h1>
          <p className="text-slate-600 mt-1">
            {isRegister ? 'Create an account to get started' : 'Sign in to continue'}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
            <input
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
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Display name <span className="text-slate-400">(optional)</span>
              </label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="input-primary w-full"
                disabled={busy}
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
            <input
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
            <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={busy || !email.trim() || !password}
            className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {isRegister ? <UserPlus size={18} /> : <LogIn size={18} />}
            {busy ? 'Please wait...' : isRegister ? 'Create account' : 'Sign in'}
          </button>
        </form>

        <button
          type="button"
          onClick={() => {
            setMode(isRegister ? 'login' : 'register')
            setError(null)
          }}
          className="text-sm text-primary-600 hover:underline w-full text-center"
        >
          {isRegister ? 'Already have an account? Sign in' : 'Need an account? Register'}
        </button>
      </motion.div>
    </div>
  )
}

export default Login
