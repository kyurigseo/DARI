import apiClient from './client'

export async function getPersonas() {
  const { data } = await apiClient.get('/rehearsal/personas/')
  return data
}

export async function startSession({ personaId, context }) {
  const { data } = await apiClient.post('/rehearsal/sessions/', {
    persona_id: personaId,
    context,
  })
  return data
}

export async function getLatestSession() {
  const { data } = await apiClient.get('/rehearsal/sessions/latest/')
  return data
}

export async function sendMessage(sessionId, content) {
  const { data } = await apiClient.post(`/rehearsal/sessions/${sessionId}/messages/`, {
    content,
  })
  return data
}

export async function endSession(sessionId) {
  const { data } = await apiClient.post(`/rehearsal/sessions/${sessionId}/end/`)
  return data
}

export async function saveFeedbackAsCard(feedbackId, category) {
  const { data } = await apiClient.post(`/rehearsal/feedback/${feedbackId}/save-card/`, {
    category,
  })
  return data
}
