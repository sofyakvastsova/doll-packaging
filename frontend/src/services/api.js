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
