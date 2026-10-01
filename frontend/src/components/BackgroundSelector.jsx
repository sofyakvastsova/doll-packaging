import { useRef } from 'react'

function BackgroundSelector({ label, options, value, onSelect, onCustomUpload }) {
  const inputRef = useRef(null)

  const handleFileChange = async (event) => {
    const file = event.target.files?.[0]
    if (!file) {
      return
    }

    const validTypes = ['image/jpeg', 'image/png', 'image/jpg']
    if (!validTypes.includes(file.type)) {
      alert('Поддерживаются только JPG, JPEG и PNG изображения.')
      event.target.value = ''
      return
    }

    const reader = new FileReader()
    reader.onload = () => {
      onCustomUpload(reader.result)
    }
    reader.readAsDataURL(file)
    event.target.value = ''
  }

  return (
    <div className="field-block">
      <label className="field-label">{label}</label>
      <div className="swatch-grid">
        {options.map((option) => {
          const selected = value?.id === option.id && value?.kind !== 'custom'
          return (
            <button
              key={option.id}
              type="button"
              className={selected ? 'swatch-item swatch-item--selected' : 'swatch-item'}
              style={{ background: option.value }}
              title={option.name}
              onClick={() => onSelect({ kind: 'preset', value: option.value, id: option.id })}
              aria-label={option.name}
            />
          )
        })}

        <button
          type="button"
          className={value?.kind === 'custom' ? 'swatch-item swatch-item--selected swatch-item--upload' : 'swatch-item swatch-item--upload'}
          onClick={() => inputRef.current?.click()}
          aria-label="Загрузить свой фон"
        >
          +
        </button>
        <input ref={inputRef} type="file" accept=".jpg,.jpeg,.png,image/jpeg,image/png" hidden onChange={handleFileChange} />
      </div>
    </div>
  )
}

export default BackgroundSelector
