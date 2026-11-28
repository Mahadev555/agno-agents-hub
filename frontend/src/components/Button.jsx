import clsx from 'clsx'

const Button = ({
  children,
  variant = 'primary',
  size = 'md',
  className = '',
  disabled = false,
  loading = false,
  loadingText = 'Creating…',
  fullWidth = false,
  onClick,
  type = 'button',
  ...props
}) => (
  <button
    className={clsx(
      'button-base',
      `button-${variant}`,
      `button-${size}`,
      fullWidth && 'w-full',
      className
    )}
    disabled={disabled || loading}
    onClick={onClick}
    type={type}
    aria-busy={loading || undefined}
    {...props}
  >
    {loading ? loadingText : children}
  </button>
)

export default Button
