import { useRef } from 'react'

const ACCEPTED_TYPES = ['image/jpeg', 'image/jpg', 'image/png']

function LogoUpload({ value, fileName, onUpload, onRemove }) {
  const inputRef = useRef(null)

  const handleFileChange = async (event) => {
    const file = event.target.files?.[0]
    if (!file) {
      return
    }

    if (!ACCEPTED_TYPES.includes(file.type)) {
      alert('Поддерживаются только JPG, JPEG и PNG логотипы.')
      event.target.value = ''
      return
    }

    const reader = new FileReader()
    reader.onload = () => {
      onUpload(reader.result, file.name)
    }
    reader.readAsDataURL(file)
    event.target.value = ''
  }

  return (
    <div className="field-block">
      <label className="field-label">Логотип</label>

      {!value ? (
        <div className="upload-area upload-area--compact">
          <input ref={inputRef} type="file" accept=".png,.jpg,.jpeg,image/png,image/jpeg" hidden onChange={handleFileChange} />
          <button type="button" className="ghost-button" onClick={() => inputRef.current?.click()}>
            Загрузить
          </button>
        </div>
      ) : (
        <div className="media-card media-card--compact">
          <img src={value} alt="Логотип упаковки" className="logo-preview" />
          <div className="media-meta">
            <span>{fileName || 'Логотип'}</span>
            <div className="media-actions">
              <button type="button" className="text-button" onClick={() => inputRef.current?.click()}>
                Заменить
              </button>
              <button type="button" className="text-button text-button--danger" onClick={onRemove}>
                Удалить
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default LogoUpload
