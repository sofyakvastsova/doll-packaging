import { useEffect, useRef, useState } from 'react'
import { uploadImage } from '../services/api'

const ACCEPTED_TYPES = ['image/jpeg', 'image/jpg', 'image/png']

function ImageUpload({ value, fileName, imageSource, onSourceChange, onUpload, onRemove }) {
  const inputRef = useRef(null)
  const [previewImage, setPreviewImage] = useState(value || '')
  const [uploadState, setUploadState] = useState(value ? 'success' : 'idle')
  const [statusMessage, setStatusMessage] = useState(value ? 'Изображение загружено' : '')

  useEffect(() => {
    if (value) {
      setPreviewImage(value)
      setUploadState('success')
      setStatusMessage('Изображение загружено')
    } else {
      setPreviewImage('')
      setUploadState('idle')
      setStatusMessage('')
    }
  }, [value])

  const handleFileChange = async (event) => {
    const file = event.target.files?.[0]
    if (!file) {
      return
    }

    const fileType = (file.type || '').toLowerCase()
    const fileExtension = file.name.split('.').pop()?.toLowerCase()
    const typeAllowed = ACCEPTED_TYPES.includes(fileType) || ['jpg', 'jpeg', 'png'].includes(fileExtension)

    if (!typeAllowed) {
      setUploadState('error')
      setStatusMessage('Поддерживаются только изображения JPG, JPEG и PNG.')
      event.target.value = ''
      return
    }

    if (file.size > 10 * 1024 * 1024) {
      setUploadState('error')
      setStatusMessage('Размер изображения не должен превышать 10 МБ.')
      event.target.value = ''
      return
    }

    const localPreview = URL.createObjectURL(file)
    setPreviewImage(localPreview)
    setUploadState('uploading')
    setStatusMessage('Загрузка...')

    const result = await uploadImage(file)

    if (!result.ok) {
      setUploadState('error')
      setStatusMessage(result.error || 'Не удалось загрузить изображение. Проверьте формат и размер файла.')
      setPreviewImage('')
      onRemove()
      event.target.value = ''
      return
    }

    const serverUrl = new URL(result.data.url, 'http://localhost:8000').toString()
    onUpload(serverUrl, file.name)
    setUploadState('success')
    setStatusMessage('Изображение загружено')
    event.target.value = ''
  }

  const handleRemove = () => {
    setPreviewImage('')
    setUploadState('idle')
    setStatusMessage('')
    onRemove()
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

          {!previewImage ? (
            <button type="button" className="ghost-button" onClick={() => inputRef.current?.click()}>
              Выбрать изображение
            </button>
          ) : (
            <div className="media-card">
              <img src={previewImage} alt="Выбранное изображение куклы" className="media-preview" />
              <div className="media-meta">
                <span>{fileName || 'Изображение'}</span>
                <div className="media-actions">
                  <button type="button" className="text-button" onClick={() => inputRef.current?.click()}>
                    Заменить
                  </button>
                  <button type="button" className="text-button text-button--danger" onClick={handleRemove}>
                    Удалить
                  </button>
                </div>
              </div>
            </div>
          )}
          {statusMessage ? <p className={`upload-status upload-status--${uploadState}`}>{statusMessage}</p> : null}
        </div>
      ) : null}
    </div>
  )
}

export default ImageUpload
