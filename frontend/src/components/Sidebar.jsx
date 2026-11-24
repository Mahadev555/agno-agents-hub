import { useEffect, useRef } from 'react'
import { Bot, LayoutDashboard, LogOut, MessageSquare, UserCircle } from 'lucide-react'
import AgentCreateModal from './AgentCreateModal'

const icons = {
  overview: LayoutDashboard,
  run: MessageSquare,
  agents: Bot,
}

const Sidebar = ({
  isDesktop,
  activeTab,
  setActiveTab,
  tabs,
  isOpen,
  onClose,
  user,
  onOpenAccount,
  onSignOut,
  createAgentOpen,
  onCloseCreateAgent,
  onAgentCreated,
}) => {
  const accountRef = useRef(null)
  const displayName = user?.display_name || user?.email || 'Account'
  const initials = displayName.slice(0, 2).toUpperCase()

  useEffect(() => {
    if (!isOpen || isDesktop) return undefined
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isDesktop, isOpen, onClose])

  const openAccount = () => {
    if (accountRef.current) accountRef.current.open = false
    onOpenAccount()
    if (!isDesktop) onClose()
  }

  const navigation = (
    <aside className="app-sidebar" id="app-navigation" aria-label="Main navigation">
      <nav className="nav-list">
        {tabs.map((tab) => {
          const Icon = icons[tab.icon]
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => {
                setActiveTab(tab.id)
                if (!isDesktop) onClose()
              }}
              aria-current={activeTab === tab.id ? 'page' : undefined}
              className={`nav-item ${activeTab === tab.id ? 'nav-item-active' : ''}`}
            >
              <Icon size={16} strokeWidth={1.5} aria-hidden="true" />
              {tab.label}
            </button>
          )
        })}
      </nav>

      <div className="account-area">
        <details ref={accountRef}>
          <summary className="account-trigger" aria-label="Open account menu">
            <span className="user-avatar" aria-hidden="true">{initials}</span>
            <span className="min-w-0 flex-1 truncate text-sm font-medium">{displayName}</span>
            <UserCircle size={16} strokeWidth={1.5} aria-hidden="true" />
          </summary>
          <div className="account-popover">
            <div className="border-b border-slate-200 px-2 py-2">
              <p className="truncate text-sm font-medium text-slate-800">{displayName}</p>
              <p className="truncate text-xs text-slate-500">{user?.email}</p>
              {user?.is_admin && <p className="mt-1 text-xs text-slate-500">Administrator</p>}
            </div>
            <button type="button" onClick={openAccount}>
              <UserCircle size={16} strokeWidth={1.5} aria-hidden="true" />
              Profile
            </button>
            <button type="button" onClick={onSignOut}>
              <LogOut size={16} strokeWidth={1.5} aria-hidden="true" />
              Sign out
            </button>
          </div>
        </details>
      </div>
    </aside>
  )

  return (
    <>
      {isDesktop
        ? navigation
        : isOpen && (
          <>
            <button
              type="button"
              className="sidebar-backdrop"
              onClick={onClose}
              aria-label="Close navigation"
            />
            {navigation}
          </>
        )}
      <AgentCreateModal
        open={createAgentOpen}
        onClose={onCloseCreateAgent}
        onCreated={onAgentCreated}
      />
    </>
  )
}

export default Sidebar
