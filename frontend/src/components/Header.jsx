import { Bot, ChevronRight, Menu, Plus } from 'lucide-react'
import Button from './Button'

const Header = ({ sidebarOpen, setSidebarOpen, currentPage, onCreateAgent }) => (
  <header className="app-header">
    <div className="flex min-w-0 items-center gap-3">
      <button
        type="button"
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="icon-button"
        aria-label={sidebarOpen ? 'Collapse navigation' : 'Open navigation'}
        aria-expanded={sidebarOpen}
        aria-controls="app-navigation"
      >
        <Menu size={16} strokeWidth={1.5} aria-hidden="true" />
      </button>
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <span className="brand-mark" aria-hidden="true">
          <Bot size={16} strokeWidth={1.5} />
        </span>
        <span className="breadcrumb-root">Agno Hub</span>
        <ChevronRight size={16} strokeWidth={1.5} aria-hidden="true" />
        <span className="breadcrumb-current" aria-current="page">{currentPage}</span>
      </nav>
    </div>

    <Button onClick={onCreateAgent}>
      <Plus size={16} strokeWidth={1.5} aria-hidden="true" />
      Create agent
    </Button>
  </header>
)

export default Header
