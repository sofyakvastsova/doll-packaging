import { useEffect, useState } from 'react'
import PackagingTypeSelector from '../components/PackagingTypeSelector'
import ImageUpload from '../components/ImageUpload'
import BackgroundSelector from '../components/BackgroundSelector'
import LogoUpload from '../components/LogoUpload'
import TextForm from '../components/TextForm'
import PackagePreview from '../components/PackagePreview'
import ServerStatus from '../components/ServerStatus'
import { checkHealth } from '../services/api'
import { outerBackgrounds, innerBackgrounds } from '../data/backgrounds'
import { ORIGINAL_MONSTER_HIGH_ACCENT } from '../data/monsterHighPalette'

const defaultOuter = outerBackgrounds[0]
const defaultInner = innerBackgrounds[0]

function PackageCreator() {
  const [packagingType, setPackagingType] = useState('monster-high')
  const [accentColor, setAccentColor] = useState(ORIGINAL_MONSTER_HIGH_ACCENT)
  const [dollImage, setDollImage] = useState('')
  const [dollImageName, setDollImageName] = useState('')
  const [uploadedPhoto, setUploadedPhoto] = useState({ url: '', filename: '' })
  const [imageSource, setImageSource] = useState('upload')
  const [outerBackground, setOuterBackground] = useState({ kind: 'preset', value: defaultOuter.value, id: defaultOuter.id })
  const [innerBackground, setInnerBackground] = useState({ kind: 'preset', value: defaultInner.value, id: defaultInner.id })
  const [logo, setLogo] = useState('')
  const [logoName, setLogoName] = useState('')
  const [dollName, setDollName] = useState('Софья')
  const [description, setDescription] = useState('Кукла создана по фотографии и оформлена в стильный ретро-пакет.')
  const [serverStatus, setServerStatus] = useState({ ok: false, checked: false })
  const [generateState, setGenerateState] = useState('')

  useEffect(() => {
    const fetchStatus = async () => {
      const result = await checkHealth()
      setServerStatus({ ...result, checked: true })
    }

    fetchStatus()
  }, [])

  const handleGenerate = () => {
    setGenerateState('Данные готовы к формированию')
  }

  return (
    <main className="page-shell">
      <header className="page-header">
        <h1>Создание персонализированной упаковки</h1>
      </header>

      <div className="creator-layout">
        <section className="preview-panel" aria-label="Предпросмотр упаковки">
          <PackagePreview
            packagingType={packagingType}
            accentColor={accentColor}
            dollImage={dollImage}
            outerBackground={outerBackground}
            innerBackground={innerBackground}
            logo={logo}
            dollName={dollName}
            description={description}
          />
        </section>

        <aside className="settings-panel" aria-label="Настройки упаковки">
          <PackagingTypeSelector value={packagingType} onChange={setPackagingType} />

          {packagingType === 'monster-high' ? (
            <div className="field-block">
              <label className="field-label" htmlFor="monster-high-accent-color">Акцентный цвет внешней коробки</label>
              <input
                id="monster-high-accent-color"
                className="accent-color-picker"
                type="color"
                value={accentColor}
                onChange={(event) => setAccentColor(event.target.value.toUpperCase())}
              />
            </div>
          ) : null}

          <ImageUpload
            value={dollImage}
            fileName={dollImageName}
            imageSource={imageSource}
            sourceImageUrl={uploadedPhoto.url}
            sourceFilename={uploadedPhoto.filename}
            style={packagingType.replace('-', '_')}
            onSourceChange={setImageSource}
            onUpload={(url, fileName, sourceFilename) => {
              setDollImage(url)
              setDollImageName(fileName)
              setUploadedPhoto({ url, filename: sourceFilename })
            }}
            onGenerated={(url, fileName) => {
              setDollImage(url)
              setDollImageName(fileName)
            }}
            onRemove={() => {
              setDollImage('')
              setDollImageName('')
              setUploadedPhoto({ url: '', filename: '' })
            }}
          />

          {packagingType === 'bratz' ? (
            <BackgroundSelector
              label="Внешний фон"
              options={outerBackgrounds}
              value={outerBackground}
              onSelect={setOuterBackground}
              onCustomUpload={(url) => setOuterBackground({ kind: 'custom', value: url, id: 'custom-outer' })}
            />
          ) : null}

          {packagingType === 'bratz' ? (
            <BackgroundSelector
              label="Внутренний фон"
              options={innerBackgrounds}
              value={innerBackground}
              onSelect={setInnerBackground}
              onCustomUpload={(url) => setInnerBackground({ kind: 'custom', value: url, id: 'custom-inner' })}
            />
          ) : null}

          <LogoUpload
            value={logo}
            fileName={logoName}
            onUpload={(url, fileName) => {
              setLogo(url)
              setLogoName(fileName)
            }}
            onRemove={() => {
              setLogo('')
              setLogoName('')
            }}
          />

          <TextForm
            dollName={dollName}
            description={description}
            onNameChange={setDollName}
            onDescriptionChange={setDescription}
          />

          <div className="toolbar">
            <ServerStatus status={serverStatus} />
            <button type="button" className="submit-button" onClick={handleGenerate}>
              Сформировать упаковку
            </button>
            {generateState ? <p className="generate-message">{generateState}</p> : null}
          </div>
        </aside>
      </div>
    </main>
  )
}

export default PackageCreator
