import { useEffect, useRef, useState } from 'react'
import PackagingTypeSelector from '../components/PackagingTypeSelector'
import ImageUpload from '../components/ImageUpload'
import BackgroundSelector from '../components/BackgroundSelector'
import LogoUpload from '../components/LogoUpload'
import TextForm from '../components/TextForm'
import PackagePreview from '../components/PackagePreview'
import ServerStatus from '../components/ServerStatus'
import { checkHealth, createProject, deleteProjectAsset, loadProject, updateProject } from '../services/api'
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
  const [project, setProject] = useState(null)
  const [projectError, setProjectError] = useState('')
  const [sourceAssetId, setSourceAssetId] = useState('')
  const [dollAssetId, setDollAssetId] = useState('')
  const [generatedAssetId, setGeneratedAssetId] = useState('')
  const [logoAssetId, setLogoAssetId] = useState('')
  const [outerBackgroundAssetId, setOuterBackgroundAssetId] = useState('')
  const [innerBackgroundAssetId, setInnerBackgroundAssetId] = useState('')
  const projectInitRef = useRef(null)
  const projectSaveQueue = useRef(Promise.resolve())

  useEffect(() => {
    let active = true
    if (!projectInitRef.current) {
      projectInitRef.current = (async () => {
        const savedCredentials = localStorage.getItem('doll-packaging-project')
        if (savedCredentials) {
          try {
            const restored = await loadProject(JSON.parse(savedCredentials))
            return restored
          } catch {
            localStorage.removeItem('doll-packaging-project')
          }
        }
        const created = await createProject('monster_high')
        if (!created.ok) throw new Error(created.error)
        const credentials = { id: created.data.id, guest_token: created.data.guest_token }
        localStorage.setItem('doll-packaging-project', JSON.stringify(credentials))
        return { ...created.data, ...credentials }
      })()
    }
    projectInitRef.current.then((loaded) => {
      if (!active) return
      setProject(loaded)
      if (loaded.style) setPackagingType(loaded.style.replace('_', '-'))
      const settings = loaded.settings || {}
      if (settings.accentColor) setAccentColor(settings.accentColor)
      if (settings.imageSource) setImageSource(settings.imageSource)
      if (settings.outerBackground) {
        setOuterBackground({ ...settings.outerBackground, value: loaded.outerBackgroundUrl || settings.outerBackground.value })
        setOuterBackgroundAssetId(loaded.outerBackgroundAsset?.id || settings.outerBackground.assetId || '')
      }
      if (settings.innerBackground) {
        setInnerBackground({ ...settings.innerBackground, value: loaded.innerBackgroundUrl || settings.innerBackground.value })
        setInnerBackgroundAssetId(loaded.innerBackgroundAsset?.id || settings.innerBackground.assetId || '')
      }
      if (settings.dollName) setDollName(settings.dollName)
      if (settings.description) setDescription(settings.description)
      if (loaded.sourceAsset) {
        setSourceAssetId(loaded.sourceAsset.id)
        setUploadedPhoto({ url: loaded.sourcePhotoUrl, filename: loaded.sourceAsset.id })
        if (!loaded.dollAsset) {
          setDollImage(loaded.sourcePhotoUrl)
          setDollImageName(loaded.sourceAsset.metadata?.original_name || loaded.sourceAsset.id)
        }
      }
      if (loaded.dollAsset) {
        setDollAssetId(loaded.dollAsset.id)
        setDollImage(loaded.dollImageUrl)
        setDollImageName(loaded.dollAsset.metadata?.original_name || loaded.dollAsset.id)
      }
      if (loaded.generatedAsset) setGeneratedAssetId(loaded.generatedAsset.id)
      if (loaded.logoAsset) {
        setLogoAssetId(loaded.logoAsset.id)
        setLogo(loaded.logoUrl)
        setLogoName(loaded.logoAsset.metadata?.original_name || loaded.logoAsset.id)
      }
    }).catch((error) => {
      if (active) setProjectError(error.message)
    })

    const fetchStatus = async () => {
      const result = await checkHealth()
      setServerStatus({ ...result, checked: true })
    }

    fetchStatus()
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!project) return
    const changes = {
      style: packagingType.replace('-', '_'),
      settings: {
        accentColor,
        imageSource,
        outerBackground: outerBackground.kind === 'custom'
          ? { ...outerBackground, value: '', assetId: outerBackgroundAssetId }
          : outerBackground,
        innerBackground: innerBackground.kind === 'custom'
          ? { ...innerBackground, value: '', assetId: innerBackgroundAssetId }
          : innerBackground,
        dollName,
        description,
        sourceAssetId,
        dollAssetId,
        generatedAssetId,
        logoAssetId,
        outerBackgroundAssetId,
        innerBackgroundAssetId,
      },
    }
    const timer = window.setTimeout(() => {
      projectSaveQueue.current = projectSaveQueue.current
        .catch(() => {})
        .then(() => updateProject(project, changes))
        .catch((error) => setProjectError(error.message))
    }, 350)
    return () => window.clearTimeout(timer)
  }, [project, packagingType, accentColor, imageSource, outerBackground, innerBackground, dollName, description, sourceAssetId, dollAssetId, generatedAssetId, logoAssetId, outerBackgroundAssetId, innerBackgroundAssetId])

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
          <fieldset className="project-controls" disabled={!project} aria-busy={!project}>
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
            project={project}
            style={packagingType.replace('-', '_')}
            onSourceChange={setImageSource}
            onUpload={(url, fileName, sourceFilename, assetId) => {
              setDollImage(url)
              setDollImageName(fileName)
              setUploadedPhoto({ url, filename: sourceFilename })
              Promise.all([sourceAssetId, dollAssetId, generatedAssetId].filter(Boolean).map((id) => deleteProjectAsset(id, project)))
                .catch((error) => setProjectError(error.message))
              if (assetId) setSourceAssetId(assetId)
              setDollAssetId('')
              setGeneratedAssetId('')
            }}
            onGenerated={(url, fileName, assetId, rawAssetId) => {
              setDollImage(url)
              setDollImageName(fileName)
              if (assetId) setDollAssetId(assetId)
              if (rawAssetId) setGeneratedAssetId(rawAssetId)
            }}
            onRemove={() => {
              Promise.all([sourceAssetId, dollAssetId, generatedAssetId].filter(Boolean).map((id) => deleteProjectAsset(id, project)))
                .catch((error) => setProjectError(error.message))
              setDollImage('')
              setDollImageName('')
              setUploadedPhoto({ url: '', filename: '' })
              setSourceAssetId('')
              setDollAssetId('')
              setGeneratedAssetId('')
            }}
          />

          {packagingType === 'bratz' ? (
            <BackgroundSelector
              label="Внешний фон"
              slot="outer_background"
              options={outerBackgrounds}
              value={outerBackground}
              project={project}
              onSelect={(selection) => {
                if (outerBackgroundAssetId) deleteProjectAsset(outerBackgroundAssetId, project).catch((error) => setProjectError(error.message))
                setOuterBackground(selection)
                setOuterBackgroundAssetId('')
              }}
              onCustomUpload={(url, assetId) => {
                if (outerBackgroundAssetId) deleteProjectAsset(outerBackgroundAssetId, project).catch((error) => setProjectError(error.message))
                setOuterBackground({ kind: 'custom', value: url, id: 'custom-outer', assetId })
                setOuterBackgroundAssetId(assetId)
              }}
            />
          ) : null}

          {packagingType === 'bratz' ? (
            <BackgroundSelector
              label="Внутренний фон"
              slot="inner_background"
              options={innerBackgrounds}
              value={innerBackground}
              project={project}
              onSelect={(selection) => {
                if (innerBackgroundAssetId) deleteProjectAsset(innerBackgroundAssetId, project).catch((error) => setProjectError(error.message))
                setInnerBackground(selection)
                setInnerBackgroundAssetId('')
              }}
              onCustomUpload={(url, assetId) => {
                if (innerBackgroundAssetId) deleteProjectAsset(innerBackgroundAssetId, project).catch((error) => setProjectError(error.message))
                setInnerBackground({ kind: 'custom', value: url, id: 'custom-inner', assetId })
                setInnerBackgroundAssetId(assetId)
              }}
            />
          ) : null}

          <LogoUpload
            value={logo}
            fileName={logoName}
            project={project}
            onUpload={(url, fileName, assetId) => {
              setLogo(url)
              setLogoName(fileName)
              if (assetId) setLogoAssetId(assetId)
            }}
            onRemove={() => {
              deleteProjectAsset(logoAssetId, project).catch((error) => setProjectError(error.message))
              setLogo('')
              setLogoName('')
              setLogoAssetId('')
            }}
          />

          <TextForm
            dollName={dollName}
            description={description}
            onNameChange={setDollName}
            onDescriptionChange={setDescription}
          />
          </fieldset>

          <div className="toolbar">
            <ServerStatus status={serverStatus} />
            <button type="button" className="submit-button" disabled={!project} onClick={handleGenerate}>
              Сформировать упаковку
            </button>
            {generateState ? <p className="generate-message">{generateState}</p> : null}
            {projectError ? <p className="upload-status upload-status--error" role="alert">{projectError}</p> : null}
          </div>
        </aside>
      </div>
    </main>
  )
}

export default PackageCreator
