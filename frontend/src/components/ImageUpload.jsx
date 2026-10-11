import { useEffect, useRef, useState } from 'react'
import { generateDollImage, uploadImage } from '../services/api'

const ACCEPTED_TYPES = ['image/jpeg', 'image/jpg', 'image/png']

function ImageUpload({
  value,
  fileName,
  imageSource,
  sourceImageUrl,
  sourceFilename,
  style,
  onSourceChange,
  onUpload,
  onGenerated,
  onRemove,
}) {
  const inputRef = useRef(null)
  const [previewImage, setPreviewImage] = useState(value || '')
  const [uploadState, setUploadState] = useState(value ? 'success' : 'idle')
  const [statusMessage, setStatusMessage] = useState(value ? 'Изображение загружено' : '')
  const [generationState, setGenerationState] = useState('idle')
  const [generationError, setGenerationError] = useState('')
  const [generationResult, setGenerationResult] = useState(null)

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
    onUpload(serverUrl, file.name, result.data.filename)
    setGenerationState('idle')
    setGenerationError('')
    setGenerationResult(null)
    setUploadState('success')
    setStatusMessage('Изображение загружено')
    event.target.value = ''
  }

  const handleGenerate = async () => {
    if (!sourceFilename || generationState === 'loading') return

    setGenerationState('loading')
    setGenerationError('')
    setGenerationResult(null)
    const result = await generateDollImage(sourceFilename, style)

    if (!result.ok) {
      setGenerationState('error')
      setGenerationError(result.error)
      return
    }

    const generatedUrl = new URL(result.data.url, 'http://localhost:8000').toString()
    setGenerationResult({ ...result.data, displayUrl: generatedUrl })
    setGenerationState('success')
    onGenerated(generatedUrl, result.data.filename)
  }

  const handleRemove = () => {
    setPreviewImage('')
    setUploadState('idle')
    setStatusMessage('')
    setGenerationState('idle')
    setGenerationError('')
    setGenerationResult(null)
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
        <div className="ai-generation" aria-busy={generationState === 'loading'}>
          {sourceImageUrl ? (
            <div className="media-card ai-generation__source">
              <img src={sourceImageUrl} alt="Исходное фото для генерации" className="media-preview" />
              <div className="media-meta">
                <span>{sourceFilename}</span>
                <span>{style === 'monster_high' ? 'Стиль Monster High' : 'Стиль Bratz'}</span>
              </div>
            </div>
          ) : (
            <div className="inline-note">
              Для генерации сначала загрузите исходное фото.
              <button type="button" className="text-button ai-generation__upload-link" onClick={() => onSourceChange('upload')}>
                Перейти к загрузке
              </button>
            </div>
          )}

          <button
            type="button"
            className="ghost-button ai-generation__button"
            disabled={!sourceFilename || generationState === 'loading'}
            onClick={handleGenerate}
          >
            {generationState === 'loading' ? 'Создаём иллюстрацию…' : generationResult ? 'Создать ещё раз' : 'Создать иллюстрацию'}
          </button>

          {generationState === 'loading' ? (
            <p className="upload-status upload-status--uploading" role="status">Запрос отправлен. Это может занять до трёх минут.</p>
          ) : null}
          {generationError ? <p className="upload-status upload-status--error" role="alert">{generationError}</p> : null}
          {generationResult ? (
            <div className="ai-generation__result" aria-label="Результат генерации">
              <img src={generationResult.displayUrl} alt="Стилизованная кукла" className="ai-generation__image" />
              <p className="ai-generation__metrics" role="status">
                Готово · PhotoPanda · {generationResult.model_id} · {generationResult.duration_ms} мс · попыток: {generationResult.attempts}
              </p>
            </div>
          ) : null}
        </div>
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
