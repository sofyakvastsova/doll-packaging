function ServerStatus({ status }) {
  const label = status?.ok ? 'Сервер: подключён' : 'Сервер: недоступен'
  const className = status?.ok ? 'status-pill status-pill--ok' : 'status-pill status-pill--error'

  return (
    <div className="status-block">
      <span className={className}>{label}</span>
      {!status?.ok && status?.error ? <p className="status-message">{status.error}</p> : null}
    </div>
  )
}

export default ServerStatus
