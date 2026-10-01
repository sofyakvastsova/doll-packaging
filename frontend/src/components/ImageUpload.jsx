import { useRef } from 'react'

const ACCEPTED_TYPES = ['image/jpeg', 'image/jpg', 'image/png']

function ImageUpload({ value, fileName, imageSource, onSourceChange, onUpload, onRemove }) {
  const inputRef = useRef(null)

  const handleFileChange = async (event) => {
    const file = event.target.files?.[0]
    if (!file) {
      return
    }

    if (!ACCEPTED_TYPES.includes(file.type)) {
      alert('Поддерживаются только JPG, JPEG и PNG изображения.')
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
      <label className="field-label">Изображение</label>

      <div className="segmented-control">
        <button
          type="button"
          className={imageSource === 'upload' ? 'segmented-button segmented-button--active' : 'segmented-button'}
          onClick={() => onSourceChange('upload')}
        >
          Загрузить
        </button>
        <button
          type="button"
          className={imageSource === 'ai' ? 'segmented-button segmented-button--active' : 'segmented-button'}
          onClick={() => onSourceChange('ai')}
        >
          Создать по фото
        </button>
      </div>

      {imageSource === 'ai' ? (
        <div className="inline-note">AI-генерация будет подключена на следующем этапе.</div>
      ) : null}

      {imageSource === 'upload' ? (
        <div className="upload-area">
          <input
            ref={inputRef}
            type="file"
            accept=".jpg,.jpeg,.png,image/jpeg,image/png"
            hidden
            onChange={handleFileChange}
          />

          {!value ? (
            <button type="button" className="ghost-button" onClick={() => inputRef.current?.click()}>
              Выбрать изображение
            </button>
          ) : (
            <div className="media-card">
              <img src={value} alt="Выбранное изображение куклы" className="media-preview" />
              <div className="media-meta">
                <span>{fileName || 'Изображение'}</span>
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
      ) : null}
    </div>
  )
}

export default ImageUpload
