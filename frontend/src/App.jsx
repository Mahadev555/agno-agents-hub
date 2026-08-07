import { useCallback, useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Header from './components/Header'
import Sidebar from './components/Sidebar'
import Dashboard from './components/Dashboard'
import ChatPlayground from './components/ChatPlayground'
import AgentComponent from './components/AgentComponent'
import Settings from './components/Settings'
import Login from './components/Login'
import { authService, setUnauthenticatedHandler } from './services/api'

const App = () => {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [sidebarOpen, setSidebarOpen] = useState(true)

  // null = signed out, undefined = still checking a stored token.
  const [user, setUser] = useState(undefined)

  const signOut = useCallback(() => {
    authService.logout()
    setUser(null)
  }, [])

  // The API layer calls this when the server rejects our token, so an expired
  // session drops to the login screen instead of rendering empty lists.
  useEffect(() => {
    setUnauthenticatedHandler(() => setUser(null))
    return () => setUnauthenticatedHandler(null)
  }, [])

  // Validate any stored token once on load.
  useEffect(() => {
    let cancelled = false

    const restore = async () => {
      if (!authService.hasToken()) {
        setUser(null)
        return
      }
      try {
        const me = await authService.me()
        if (!cancelled) setUser(me)
      } catch {
        // The interceptor already cleared the token.
        if (!cancelled) setUser(null)
      }
    }

    restore()
    return () => {
      cancelled = true
    }
  }, [])

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'chat', label: 'Chat', icon: '💬' },
    { id: 'agents', label: 'Agents', icon: '🤖' },
    { id: 'settings', label: 'Settings', icon: '⚙️' },
  ]

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard />
      case 'chat':
        return <ChatPlayground />
      case 'agents':
        return <AgentComponent />
      case 'settings':
        return <Settings />
      default:
        return <Dashboard />
    }
  }

  if (user === undefined) {
    return (
      <div className="min-h-screen flex items-center justify-center text-slate-500">
        Loading...
      </div>
    )
  }

  if (user === null) {
    return <Login onAuthenticated={setUser} />
  }

  return (
    <div className="min-h-screen gradient-hero">
      <Header
        sidebarOpen={sidebarOpen}
        setSidebarOpen={setSidebarOpen}
        user={user}
        onSignOut={signOut}
      />

      <div className="flex pt-16 h-[calc(100vh-64px)]">
        {/* Sidebar */}
        <Sidebar
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          tabs={tabs}
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />

        {/* Main Content */}
        <main className="flex-1 overflow-auto">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3 }}
              className="p-6"
            >
              {renderContent()}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}

export default App
