import { useEffect, useId, useRef, useState } from 'react'
import { Check, ChevronDown } from 'lucide-react'

const Select = ({
  id,
  label,
  value,
  options,
  onChange,
  placeholder = 'Select an option',
  disabled = false,
  loading = false,
}) => {
  const generatedId = useId()
  const controlId = id || generatedId
  const labelId = `${controlId}-label`
  const listId = `${controlId}-listbox`
  const rootRef = useRef(null)
  const selectedIndex = options.findIndex((option) => option.value === value)
  const selectedOption = selectedIndex >= 0 ? options[selectedIndex] : null
  const [open, setOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(Math.max(selectedIndex, 0))

  useEffect(() => {
    if (!open) return undefined

    const handlePointerDown = (event) => {
      if (event.target instanceof Node && !rootRef.current?.contains(event.target)) {
        setOpen(false)
      }
    }

    document.addEventListener('pointerdown', handlePointerDown)
    return () => document.removeEventListener('pointerdown', handlePointerDown)
  }, [open])

  useEffect(() => {
    if (open) {
      document.getElementById(`${listId}-option-${activeIndex}`)
        ?.scrollIntoView({ block: 'nearest' })
    }
  }, [activeIndex, listId, open])

  const chooseOption = (index) => {
    const option = options[index]
    if (!option) return
    onChange(option.value)
    setActiveIndex(index)
    setOpen(false)
  }

  const toggleOpen = () => {
    if (open) {
      setOpen(false)
      return
    }
    setActiveIndex(Math.max(selectedIndex, 0))
    setOpen(true)
  }

  const handleKeyDown = (event) => {
    if (disabled || options.length === 0) return

    if (event.key === 'Escape') {
      if (open) {
        event.preventDefault()
        setOpen(false)
      }
      return
    }

    if (event.key === 'Tab') {
      setOpen(false)
      return
    }

    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      const step = event.key === 'ArrowDown' ? 1 : -1
      if (!open) {
        setActiveIndex(selectedIndex >= 0 ? selectedIndex : (step > 0 ? 0 : options.length - 1))
        setOpen(true)
      } else {
        setActiveIndex((index) => (index + step + options.length) % options.length)
      }
      return
    }

    if (event.key === 'Home' || event.key === 'End') {
      event.preventDefault()
      setActiveIndex(event.key === 'Home' ? 0 : options.length - 1)
      setOpen(true)
      return
    }

    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      if (open) chooseOption(activeIndex)
      else {
        setActiveIndex(Math.max(selectedIndex, 0))
        setOpen(true)
      }
    }
  }

  return (
    <div className="select-field">
      <label id={labelId} className="field-label" htmlFor={controlId}>{label}</label>
      <div className="select-root" ref={rootRef}>
        <button
          type="button"
          id={controlId}
          className="select-trigger"
          disabled={disabled || loading || options.length === 0}
          role="combobox"
          aria-autocomplete="none"
          aria-busy={loading || undefined}
          aria-labelledby={`${labelId} ${controlId}-value`}
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-controls={listId}
          aria-activedescendant={open ? `${listId}-option-${activeIndex}` : undefined}
          onClick={toggleOpen}
          onKeyDown={handleKeyDown}
        >
          <span className="select-trigger-copy">
            <span id={`${controlId}-value`} className={selectedOption ? 'select-option-label' : 'select-placeholder'}>
              {selectedOption?.label || placeholder}
            </span>
            {selectedOption?.description && (
              <span className="select-option-description">{selectedOption.description}</span>
            )}
          </span>
          <ChevronDown size={16} strokeWidth={1.5} aria-hidden="true" />
        </button>
        <div
          id={listId}
          className="select-listbox"
          role="listbox"
          aria-labelledby={labelId}
          hidden={!open}
        >
          {options.map((option, index) => (
            <div
              id={`${listId}-option-${index}`}
              key={option.value}
              className={`select-option ${index === activeIndex ? 'select-option-active' : ''}`}
              role="option"
              aria-selected={option.value === value}
              onMouseEnter={() => setActiveIndex(index)}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => chooseOption(index)}
            >
              <span className="select-option-copy">
                <span className="select-option-label">{option.label}</span>
                {option.description && (
                  <span className="select-option-description">{option.description}</span>
                )}
              </span>
              {option.value === value && <Check size={16} strokeWidth={1.5} aria-hidden="true" />}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default Select
