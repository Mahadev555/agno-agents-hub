import { Menu, Plus } from 'lucide-react'
import Button from './Button'

const Header = ({ isDesktop, sidebarOpen, setSidebarOpen, onCreateAgent }) => (
  <header className="app-header">
    <div className="header-brand">
      {!isDesktop && (
        <button
          type="button"
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="icon-button"
          aria-label={sidebarOpen ? 'Close navigation' : 'Open navigation'}
          aria-expanded={sidebarOpen}
          aria-controls="app-navigation"
        >
          <Menu size={16} strokeWidth={1.5} aria-hidden="true" />
        </button>
      )}
      <img className="header-logo" src="/agno-icon.svg" alt="" />
      <span>Agno Hub</span>
    </div>

    <div className="header-actions">
      <Button onClick={onCreateAgent}>
        <Plus size={16} strokeWidth={1.5} aria-hidden="true" />
        Create agent
      </Button>
    </div>
  </header>
)

export default Header
