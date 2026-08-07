import { motion, AnimatePresence } from 'framer-motion'
import { Menu, X, Bell, Settings, LogOut } from 'lucide-react'
import { useState } from 'react'

const Header = ({ sidebarOpen, setSidebarOpen, user, onSignOut }) => {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <motion.header
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="fixed top-0 left-0 right-0 z-40 backdrop-blur-md bg-white/80 border-b border-white/20 shadow-lg"
    >
      <div className="flex justify-between items-center h-16 px-6">
        {/* Logo Section */}
        <div className="flex items-center gap-4">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
          >
            {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
          </motion.button>
          <motion.div
            whileHover={{ scale: 1.05 }}
            className="text-2xl font-bold gradient-text flex items-center gap-2"
          >
            🤖 Agno Hub
          </motion.div>
        </div>

        {/* Right Section */}
        <div className="flex items-center gap-4">
          {/* Notifications */}
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="relative p-2 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <Bell size={20} className="text-slate-700" />
            <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
          </motion.button>

          {/* Profile Menu */}
          <div className="relative">
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setMenuOpen(!menuOpen)}
              className="w-10 h-10 rounded-lg bg-gradient-to-r from-primary-500 to-primary-600 text-white font-bold flex items-center justify-center hover:shadow-lg transition-all"
              title={user?.email}
            >
              {(user?.display_name || user?.email || 'AH').slice(0, 2).toUpperCase()}
            </motion.button>

            <AnimatePresence>
              {menuOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="absolute top-12 right-0 w-56 bg-white rounded-lg shadow-lg border border-slate-200 overflow-hidden"
                >
                  {user && (
                    <div className="px-4 py-3 border-b border-slate-200">
                      <div className="text-sm font-medium text-slate-900 truncate">
                        {user.display_name || user.email}
                      </div>
                      <div className="text-xs text-slate-500 truncate">{user.email}</div>
                      {user.is_admin && (
                        <span className="inline-block mt-1 text-xs px-2 py-0.5 rounded bg-primary-100 text-primary-700">
                          admin
                        </span>
                      )}
                    </div>
                  )}
                  <button
                    onClick={() => {
                      setMenuOpen(false)
                      onSignOut?.()
                    }}
                    className="w-full px-4 py-2 text-left hover:bg-slate-50 transition-colors flex items-center gap-2 text-red-600"
                  >
                    <LogOut size={18} />
                    Sign out
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </motion.header>
  )
}

export default Header
