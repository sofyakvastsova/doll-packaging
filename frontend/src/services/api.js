const API_BASE_URL = 'http://localhost:8000'

export async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const payload = await response.json()
    return { ok: true, data: payload }
  } catch (error) {
    const reason = error instanceof Error ? error.message : 'Неизвестная ошибка'

    return {
      ok: false,
      error: `Сервер недоступен. Проверьте, что FastAPI запущен на localhost:8000. Причина: ${reason}`,
    }
  }
}

export async function uploadImage(file) {
  if (!file) {
    return { ok: false, error: 'Файл не найден.' }
  }

  const formData = new FormData()
  formData.append('file', file)

  try {
    const response = await fetch(`${API_BASE_URL}/api/images/upload`, {
      method: 'POST',
      body: formData,
    })

    const payload = await response.json().catch(() => null)

    if (!response.ok) {
      const message = payload?.detail || 'Не удалось загрузить изображение.'
      return { ok: false, error: message }
    }

    return { ok: true, data: payload }
  } catch (error) {
    return {
      ok: false,
      error: 'Не удалось загрузить изображение. Проверьте соединение с сервером.',
    }
  }
}

export async function generateDollImage(sourceFilename, style) {
  if (!sourceFilename) {
    return { ok: false, error: 'Сначала загрузите исходное фото.' }
  }

  const formData = new FormData()
  formData.append('source_filename', sourceFilename)
  formData.append('style', style)

  try {
    const response = await fetch(`${API_BASE_URL}/api/images/generate`, {
      method: 'POST',
      body: formData,
    })
    const payload = await response.json().catch(() => null)

    if (!response.ok) {
      return { ok: false, error: payload?.detail || 'Не удалось создать иллюстрацию.' }
    }

    return { ok: true, data: payload }
  } catch {
    return { ok: false, error: 'Не удалось связаться с PhotoPanda. Исходное фото сохранено.' }
  }
}

export async function createProject(style, settings = {}) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ style, settings }),
    })
    const payload = await response.json().catch(() => null)
    if (!response.ok) return { ok: false, error: payload?.detail || 'Не удалось создать проект.' }
    return { ok: true, data: payload }
  } catch {
    return { ok: false, error: 'Не удалось создать проект. Проверьте соединение с сервером.' }
  }
}

export async function loadProject(project) {
  const response = await fetch(`${API_BASE_URL}/api/projects/${project.id}`, {
    headers: { 'X-Guest-Token': project.guest_token },
  })
  if (!response.ok) throw new Error('Не удалось открыть сохранённый проект.')
  const snapshot = await response.json()
  const latestAsset = (type) => snapshot.assets.filter((asset) => asset.asset_type === type).at(-1)
  const source = latestAsset('original_photo')
  const doll = latestAsset('transparent_doll') || latestAsset('generated_doll')
  const generated = latestAsset('generated_doll')
  const logo = latestAsset('logo')
  const outerBackground = snapshot.assets.find((asset) => asset.asset_type === 'intermediate' && asset.metadata?.slot === 'outer_background')
  const innerBackground = snapshot.assets.find((asset) => asset.asset_type === 'intermediate' && asset.metadata?.slot === 'inner_background')
  return {
    ...snapshot,
    guest_token: project.guest_token,
    sourceAsset: source,
    dollAsset: doll,
    generatedAsset: generated,
    logoAsset: logo,
    outerBackgroundAsset: outerBackground,
    innerBackgroundAsset: innerBackground,
    sourcePhotoUrl: source ? await loadPrivateAsset(source.url, project) : '',
    dollImageUrl: doll ? await loadPrivateAsset(doll.url, project) : '',
    logoUrl: logo ? await loadPrivateAsset(logo.url, project) : '',
    outerBackgroundUrl: outerBackground ? await loadPrivateAsset(outerBackground.url, project) : '',
    innerBackgroundUrl: innerBackground ? await loadPrivateAsset(innerBackground.url, project) : '',
  }
}

export async function updateProject(project, changes) {
  const response = await fetch(`${API_BASE_URL}/api/projects/${project.id}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'X-Guest-Token': project.guest_token,
    },
    body: JSON.stringify(changes),
  })
  if (!response.ok) throw new Error('Не удалось сохранить проект.')
  return response.json()
}

async function loadPrivateAsset(url, project) {
  const response = await fetch(new URL(url, API_BASE_URL), {
    headers: { 'X-Guest-Token': project.guest_token },
  })
  if (!response.ok) throw new Error('Не удалось открыть файл проекта.')
  return URL.createObjectURL(await response.blob())
}

export async function uploadProjectAsset(file, assetType, project, metadata = {}) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('asset_type', assetType)
  formData.append('asset_metadata', JSON.stringify(metadata))
  const response = await fetch(`${API_BASE_URL}/api/projects/${project.id}/assets`, {
    method: 'POST',
    headers: { 'X-Guest-Token': project.guest_token },
    body: formData,
  })
  const payload = await response.json().catch(() => null)
  if (!response.ok) return { ok: false, error: payload?.detail || 'Не удалось загрузить файл проекта.' }
  try {
    return { ok: true, data: { ...payload, filename: payload.id, url: await loadPrivateAsset(payload.url, project) } }
  } catch (error) {
    return { ok: false, error: error.message }
  }
}

export async function deleteProjectAsset(assetId, project) {
  if (!assetId || !project) return
  const response = await fetch(`${API_BASE_URL}/api/projects/${project.id}/assets/${assetId}`, {
    method: 'DELETE',
    headers: { 'X-Guest-Token': project.guest_token },
  })
  if (!response.ok && response.status !== 404) throw new Error('Не удалось удалить файл проекта.')
}

export async function generateProjectDoll(sourceAssetId, style, project) {
  const formData = new FormData()
  formData.append('source_filename', sourceAssetId)
  formData.append('style', style)
  formData.append('project_id', project.id)
  formData.append('guest_token', project.guest_token)
  try {
    const response = await fetch(`${API_BASE_URL}/api/images/generate`, { method: 'POST', body: formData })
    const payload = await response.json().catch(() => null)
    if (!response.ok) return { ok: false, error: payload?.detail || 'Не удалось создать иллюстрацию.' }
    return { ok: true, data: { ...payload, filename: payload.id, url: await loadPrivateAsset(payload.url, project) } }
  } catch (error) {
    return { ok: false, error: error.message || 'Не удалось связаться с PhotoPanda.' }
  }
}
