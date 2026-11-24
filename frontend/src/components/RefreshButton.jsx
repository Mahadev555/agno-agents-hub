import { Loader2, RefreshCw } from 'lucide-react'
import Button from './Button'

const RefreshButton = ({ loading, onClick }) => (
  <Button
    variant="secondary"
    size="sm"
    onClick={onClick}
    disabled={loading}
    aria-busy={loading}
  >
    {loading
      ? <Loader2 className="refresh-spinner" size={14} aria-hidden="true" />
      : <RefreshCw size={14} aria-hidden="true" />}
    {loading ? 'Refreshing…' : 'Refresh'}
  </Button>
)

export default RefreshButton
