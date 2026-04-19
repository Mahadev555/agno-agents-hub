import { motion } from 'framer-motion'
import { Settings as SettingsIcon, Bell, Shield, Moon } from 'lucide-react'
import Button from './Button'

const Settings = () => {
  return (
    <div className="space-y-8 max-w-4xl">
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-4xl font-bold gradient-text">Settings</h1>
        <p className="text-slate-600 mt-2">Manage your application preferences</p>
      </motion.div>

      {/* General Settings */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="card p-6">
        <div className="flex items-center gap-3 mb-6">
          <SettingsIcon size={24} className="text-primary-600" />
          <h2 className="text-xl font-bold">General Settings</h2>
        </div>

        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Application Name
            </label>
            <input
              type="text"
              defaultValue="Agno Hub"
              className="input-primary"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              API Endpoint
            </label>
            <input
              type="text"
              defaultValue="http://localhost:5000"
              className="input-primary"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Default Timeout (seconds)
            </label>
            <input
              type="number"
              defaultValue="30"
              className="input-primary"
            />
          </div>
        </div>
      </motion.div>

      {/* Notification Settings */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="card p-6">
        <div className="flex items-center gap-3 mb-6">
          <Bell size={24} className="text-primary-600" />
          <h2 className="text-xl font-bold">Notifications</h2>
        </div>

        <div className="space-y-4">
          {['Execution Complete', 'Errors', 'Updates'].map(item => (
            <div key={item} className="flex items-center justify-between">
              <label className="text-slate-700 font-medium">{item}</label>
              <motion.button
                whileHover={{ scale: 1.05 }}
                className="relative w-14 h-8 bg-emerald-500 rounded-full transition-all"
              >
                <motion.div
                  className="absolute top-1 right-1 w-6 h-6 bg-white rounded-full shadow-md"
                  initial={{ x: 0 }}
                />
              </motion.button>
            </div>
          ))}
        </div>
      </motion.div>

      {/* Security Settings */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="card p-6">
        <div className="flex items-center gap-3 mb-6">
          <Shield size={24} className="text-primary-600" />
          <h2 className="text-xl font-bold">Security</h2>
        </div>

        <div className="space-y-4">
          <Button variant="secondary" fullWidth>Change Password</Button>
          <Button variant="secondary" fullWidth>Enable Two-Factor Authentication</Button>
          <Button variant="outline" fullWidth>View Active Sessions</Button>
        </div>
      </motion.div>

      {/* Appearance Settings */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="card p-6">
        <div className="flex items-center gap-3 mb-6">
          <Moon size={24} className="text-primary-600" />
          <h2 className="text-xl font-bold">Appearance</h2>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-3">Theme</label>
            <div className="flex gap-3">
              {['Light', 'Dark', 'Auto'].map(theme => (
                <motion.button
                  key={theme}
                  whileHover={{ scale: 1.05 }}
                  className={`px-4 py-2 rounded-lg font-medium transition-all ${
                    theme === 'Light'
                      ? 'bg-gradient-to-r from-primary-500 to-primary-600 text-white'
                      : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
                  }`}
                >
                  {theme}
                </motion.button>
              ))}
            </div>
          </div>
        </div>
      </motion.div>

      {/* Danger Zone */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="card p-6 border-l-4 border-red-500">
        <h2 className="text-xl font-bold text-red-600 mb-4">Danger Zone</h2>
        <div className="space-y-3">
          <p className="text-sm text-slate-600">These actions cannot be undone.</p>
          <Button variant="secondary" fullWidth className="text-red-600 border-red-500 hover:bg-red-50">
            Clear All Data
          </Button>
          <Button variant="secondary" fullWidth className="text-red-600 border-red-500 hover:bg-red-50">
            Reset to Defaults
          </Button>
        </div>
      </motion.div>

      {/* Save Button */}
      <div className="flex gap-3 pt-6">
        <Button variant="secondary" size="lg">Cancel</Button>
        <Button variant="primary" size="lg" fullWidth>Save Changes</Button>
      </div>
    </div>
  )
}

export default Settings
