import { useCallback, useEffect, useMemo, useState } from 'react'
import Header from './components/Header'
import Sidebar from './components/Sidebar'
import Dashboard from './components/Dashboard'
import ChatPlayground from './components/ChatPlayground'
import AgentComponent from './components/AgentComponent'
import Settings from './components/Settings'
import Login from './components/Login'
import PageContainer from './components/PageContainer'
import PageHeader from './components/PageHeader'
import { authService, setUnauthenticatedHandler } from './services/api'
import { useMediaQuery } from './hooks/useMediaQuery'
import { X } from 'lucide-react'

const App = () => {
  const [activeTab, setActiveTab] = useState('dashboard')
  const isDesktop = useMediaQuery('(min-width: 1024px)')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [selectedAgentId, setSelectedAgentId] = useState(null)
  const [selectedHostAgentId, setSelectedHostAgentId] = useState(null)
  const [agentRefreshKey, setAgentRefreshKey] = useState(0)
  const [createAgentOpen, setCreateAgentOpen] = useState(false)
  const [toast, setToast] = useState(null)

  // null = signed out, undefined = still checking a stored token.
  const [user, setUser] = useState(undefined)
  const [authNotice, setAuthNotice] = useState(null)

  useEffect(() => {
    if (isDesktop) setSidebarOpen(false)
  }, [isDesktop])

  const signOut = useCallback(() => {
    authService.logout()
    setUser(null)
    setAuthNotice(null)
    setActiveTab('dashboard')
    setSelectedAgentId(null)
    setSelectedHostAgentId(null)
  }, [])

  // The API layer calls this when the server rejects our token, so an expired
  // session drops to the login screen instead of rendering empty lists.
  useEffect(() => {
    setUnauthenticatedHandler(() => {
      setAuthNotice('Your session expired. Sign in again.')
      setUser(null)
    })
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
      } catch (error) {
        if (!cancelled) {
          setUser(null)
          setAuthNotice(
            error.status === 401
              ? 'Your session expired. Sign in again.'
              : 'Could not verify your session. Check your connection, then sign in again.'
          )
        }
      }
    }

    restore()
    return () => {
      cancelled = true
    }
  }, [])

  const tabs = [
    { id: 'dashboard', label: 'Overview', icon: 'overview' },
    { id: 'chat', label: 'Run agent', icon: 'run' },
    { id: 'agents', label: 'Agents', icon: 'agents' },
  ]

  const pageTitle = useMemo(() => ({
    dashboard: 'Overview',
    chat: 'Run agent',
    agents: 'Agents',
    settings: 'Profile',
  }[activeTab] || 'Overview'), [activeTab])

  useEffect(() => {
    document.title = user ? `${pageTitle} · Agno Hub` : 'Agno Hub'
  }, [pageTitle, user])

  const notify = useCallback((message, tone = 'success') => {
    setToast({ id: Date.now(), message, tone })
  }, [])
  const closeCreateAgent = useCallback(() => setCreateAgentOpen(false), [])
  const openCreateAgent = useCallback(() => setCreateAgentOpen(true), [])
  const openAccount = useCallback(() => setActiveTab('settings'), [])
  const openAgents = useCallback(() => setActiveTab('agents'), [])
  const closeSidebar = useCallback(() => setSidebarOpen(false), [])
  const clearSelectedAgent = useCallback(() => setSelectedAgentId(null), [])

  useEffect(() => {
    if (!toast) return undefined
    const timer = window.setTimeout(() => setToast(null), 3500)
    return () => window.clearTimeout(timer)
  }, [toast])

  const runAgent = useCallback((agentId, isCoordinator = false) => {
    setSelectedAgentId(isCoordinator ? null : String(agentId))
    setSelectedHostAgentId(isCoordinator ? String(agentId) : null)
    setActiveTab('chat')
  }, [])

  const viewAgent = useCallback((agent) => {
    setSelectedAgentId(String(agent.agent_id || agent.id))
    setSelectedHostAgentId(null)
    setActiveTab('agents')
  }, [])

  const handleAgentCreated = useCallback(() => {
    setAgentRefreshKey((key) => key + 1)
    setActiveTab('agents')
    notify('Agent created')
  }, [notify])

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return (
          <Dashboard
            onExecuteAgent={runAgent}
            onViewAgent={viewAgent}
            onViewAgents={openAgents}
            onCreateAgent={openCreateAgent}
            onToast={notify}
          />
        )
      case 'chat':
        return (
          <ChatPlayground
            initialAgentId={selectedAgentId}
            initialHostAgentId={selectedHostAgentId}
            onToast={notify}
          />
        )
      case 'agents':
        return (
          <AgentComponent
            selectedAgentId={selectedAgentId}
            onExecuteAgent={runAgent}
            onSelectionHandled={clearSelectedAgent}
            onCreateAgent={openCreateAgent}
            onToast={notify}
            refreshKey={agentRefreshKey}
          />
        )
      case 'settings':
        return <Settings user={user} />
      default:
        return <Dashboard />
    }
  }

  if (user === undefined) {
    return (
      <div className="loading-screen" role="status">
        <span className="skeleton h-4 w-32" />
        <span className="sr-only">Loading Agno Hub</span>
      </div>
    )
  }

  if (user === null) {
    return (
      <Login
        notice={authNotice}
        onAuthenticated={(authenticatedUser) => {
          setAuthNotice(null)
          setUser(authenticatedUser)
        }}
      />
    )
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to content</a>
      <Header
        isDesktop={isDesktop}
        sidebarOpen={sidebarOpen}
        setSidebarOpen={setSidebarOpen}
        onCreateAgent={openCreateAgent}
      />

      <div className="app-workspace">
        <Sidebar
          isDesktop={isDesktop}
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          tabs={tabs}
          isOpen={sidebarOpen}
          onClose={closeSidebar}
          user={user}
          onOpenAccount={openAccount}
          onSignOut={signOut}
          createAgentOpen={createAgentOpen}
          onCloseCreateAgent={closeCreateAgent}
          onAgentCreated={handleAgentCreated}
        />

        <main className="app-main" id="main-content" tabIndex="-1">
          <PageContainer key={activeTab}>
            <PageHeader title={pageTitle} />
            {renderContent()}
          </PageContainer>
        </main>
      </div>
      {toast && (
        <div className="toast-region" aria-live="polite">
          <div className={`toast ${toast.tone === 'danger' ? 'toast-danger' : ''}`} role="status">
            <span>{toast.message}</span>
            <button
              type="button"
              className="icon-button"
              onClick={() => setToast(null)}
              aria-label="Dismiss notification"
            >
              <X size={16} aria-hidden="true" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
