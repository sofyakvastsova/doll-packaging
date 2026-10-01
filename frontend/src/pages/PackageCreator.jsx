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

const defaultOuter = outerBackgrounds[0]
const defaultInner = innerBackgrounds[0]

function PackageCreator() {
  const [packagingType, setPackagingType] = useState('bratz')
  const [dollImage, setDollImage] = useState('')
  const [dollImageName, setDollImageName] = useState('')
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

          <ImageUpload
            value={dollImage}
            fileName={dollImageName}
            imageSource={imageSource}
            onSourceChange={setImageSource}
            onUpload={(url, fileName) => {
              setDollImage(url)
              setDollImageName(fileName)
            }}
            onRemove={() => {
              setDollImage('')
              setDollImageName('')
            }}
          />

          <BackgroundSelector
            label="Внешний фон"
            options={outerBackgrounds}
            value={outerBackground}
            onSelect={setOuterBackground}
            onCustomUpload={(url) => setOuterBackground({ kind: 'custom', value: url, id: 'custom-outer' })}
          />

          <BackgroundSelector
            label="Внутренний фон"
            options={innerBackgrounds}
            value={innerBackground}
            onSelect={setInnerBackground}
            onCustomUpload={(url) => setInnerBackground({ kind: 'custom', value: url, id: 'custom-inner' })}
          />

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
