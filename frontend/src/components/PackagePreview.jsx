function PackagePreview({
  packagingType,
  dollImage,
  outerBackground,
  innerBackground,
  logo,
  dollName,
  description,
}) {
  const typeTheme = packagingType === 'monster-high' ? 'monster-high' : 'bratz'
  const safeName = dollName.trim() || 'Имя куклы'
  const safeDescription = description.trim() || 'Описание появится здесь.'

  const outerStyle = {
    background: outerBackground?.value || 'linear-gradient(135deg, #ffd8ea 0%, #ffc7dd 35%, #f8a5c8 100%)',
  }

  const innerStyle = {
    background: innerBackground?.value || 'linear-gradient(135deg, #fff9f4 0%, #f5e5d8 35%, #ebd2c3 100%)',
  }

  return (
    <div className={`package-preview package-preview--${typeTheme}`}>
      <div className="preview-card preview-card--front" style={outerStyle}>
        <div className="preview-inner" style={innerStyle}>
          <div className="preview-header">
            <span className="badge">{packagingType === 'monster-high' ? 'Monster High' : 'Bratz'}</span>
          </div>

          <div className="preview-doll-wrap">
            {dollImage ? (
              <img src={dollImage} alt="Кукла" className="preview-doll" />
            ) : (
              <div className="preview-placeholder">Фото куклы</div>
            )}
          </div>

          {logo ? <img src={logo} alt="Логотип" className="preview-logo" /> : null}
          <div className="preview-name">{safeName}</div>
        </div>
      </div>

      <div className="preview-card preview-card--back" style={outerStyle}>
        <div className="preview-inner preview-inner--back" style={innerStyle}>
          {dollImage ? <img src={dollImage} alt="Кукла в фоне упаковки" className="preview-doll-back" /> : <div className="preview-placeholder preview-placeholder--large">Фоновое изображение</div>}
          <div className="preview-copy">
            <span className="badge badge--muted">История</span>
            <p>{safeDescription}</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default PackagePreview
