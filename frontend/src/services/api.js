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
