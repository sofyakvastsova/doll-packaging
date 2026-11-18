import { useEffect, useState } from 'react'
import { createMonsterHighSvg, monsterHighSheets } from '../data/monsterHighPalette'
import bratzSheet20 from '../../../templates/bratz/A4 - 20.svg?url'
import bratzSheet21 from '../../../templates/bratz/A4 - 21.svg?url'
import bratzSheet24 from '../../../templates/bratz/A4 - 24.svg?url'
import bratzSheet25 from '../../../templates/bratz/A4 - 25.svg?url'
import bratzBlister from '../../../templates/bratz/блитсер.svg?url'

const bratzSheets = [
  { name: 'Лист 1', url: bratzSheet20 },
  { name: 'Лист 2', url: bratzSheet21 },
  { name: 'Лист 3', url: bratzSheet24 },
  { name: 'Лист 4', url: bratzSheet25 },
  { name: 'Блистер', url: bratzBlister },
]

function PackagePreview({
  packagingType,
  accentColor,
  dollImage,
}) {
  const [monsterHighSvgSources, setMonsterHighSvgSources] = useState([])

  useEffect(() => {
    let active = true

    Promise.all(monsterHighSheets.map((url) => fetch(url).then((response) => {
      if (!response.ok) throw new Error('Не удалось загрузить шаблон')
      return response.text()
    })))
      .then((sources) => {
        if (active) setMonsterHighSvgSources(sources)
      })
      .catch(() => {
        if (active) setMonsterHighSvgSources(null)
      })

    return () => {
      active = false
    }
  }, [])

  if (packagingType === 'monster-high') {
    return (
      <div className="package-preview package-preview--monster-high">
        {monsterHighSvgSources === null ? (
          <span className="template-loading" role="alert">Не удалось загрузить шаблон Monster High.</span>
        ) : monsterHighSvgSources.length === 0 ? (
          <span className="template-loading">Загрузка шаблона…</span>
        ) : (
          <div className="bratz-sheets" aria-label="Листы шаблона Monster High">
            {monsterHighSvgSources.map((source, index) => (
              <figure className="bratz-sheet" key={monsterHighSheets[index]}>
                <div className="monster-high-sheet">
                  <div className="monster-high-template" dangerouslySetInnerHTML={{ __html: createMonsterHighSvg(source, accentColor) }} />
                  {index === 1 && dollImage ? <img src={dollImage} alt="Кукла" className="monster-high-doll" /> : null}
                </div>
                <figcaption>Лист {index + 1}</figcaption>
              </figure>
            ))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="package-preview package-preview--bratz">
        <div className="bratz-sheets" aria-label="Листы шаблона Bratz">
          {bratzSheets.map((sheet) => (
            <figure className="bratz-sheet" key={sheet.name}>
              {sheet.url === bratzSheet20 || sheet.url === bratzSheet21 ? (
                <div className="bratz-sheet-art">
                  <img className="bratz-sheet-background" src={sheet.url} alt={`Bratz: ${sheet.name}`} />
                  {dollImage ? <img src={dollImage} alt="Кукла" className={sheet.url === bratzSheet20 ? 'bratz-doll-half' : 'bratz-doll'} /> : null}
                </div>
              ) : (
                <img src={sheet.url} alt={`Bratz: ${sheet.name}`} />
              )}
              <figcaption>{sheet.name}</figcaption>
            </figure>
          ))}
        </div>
    </div>
  )
}

export default PackagePreview
