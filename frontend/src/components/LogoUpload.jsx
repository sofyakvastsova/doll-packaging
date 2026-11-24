import { useRef } from 'react'
import { uploadProjectAsset } from '../services/api'

const ACCEPTED_TYPES = ['image/jpeg', 'image/jpg', 'image/png']

function LogoUpload({ value, fileName, project, onUpload, onRemove }) {
  const inputRef = useRef(null)

  const handleFileChange = async (event) => {
    const file = event.target.files?.[0]
    if (!file) {
      return
    }
    if (!project) {
      event.target.value = ''
      return
    }

    if (!ACCEPTED_TYPES.includes(file.type)) {
      alert('Поддерживаются только JPG, JPEG и PNG логотипы.')
      event.target.value = ''
      return
    }

    const result = await uploadProjectAsset(file, 'logo', project)
    if (!result.ok) {
      alert(result.error)
      event.target.value = ''
      return
    }
    onUpload(result.data.url, file.name, result.data.id)
    event.target.value = ''
  }

  return (
    <div className="field-block">
      <label className="field-label">Логотип</label>

      {!value ? (
        <div className="upload-area upload-area--compact">
          <input ref={inputRef} type="file" accept=".png,.jpg,.jpeg,image/png,image/jpeg" hidden onChange={handleFileChange} />
          <button type="button" className="ghost-button" disabled={!project} onClick={() => inputRef.current?.click()}>
            Загрузить
          </button>
        </div>
      ) : (
        <div className="media-card media-card--compact">
          <img src={value} alt="Логотип упаковки" className="logo-preview" />
          <div className="media-meta">
            <span>{fileName || 'Логотип'}</span>
            <div className="media-actions">
                  <button type="button" className="text-button" disabled={!project} onClick={() => inputRef.current?.click()}>
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
