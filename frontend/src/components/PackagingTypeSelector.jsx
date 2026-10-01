function PackagingTypeSelector({ value, onChange }) {
  const options = [
    { id: 'bratz', label: 'Bratz' },
    { id: 'monster-high', label: 'Monster High' },
  ]

  return (
    <div className="field-block">
      <label className="field-label">Упаковка</label>
      <div className="type-grid">
        {options.map((option) => {
          const selected = value === option.id
          return (
            <button
              key={option.id}
              type="button"
              className={`type-card ${selected ? 'type-card--active' : ''}`}
              onClick={() => onChange(option.id)}
            >
              <span className="type-card__title">{option.label}</span>
              <span className="type-card__mini" aria-hidden="true">
                {option.id === 'bratz' ? '🌸' : '🩷'}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default PackagingTypeSelector
