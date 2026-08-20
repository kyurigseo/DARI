import apiClient from './client'

export async function getCards(params = {}) {
  const { data } = await apiClient.get('/cards/', { params })
  return data
}

export async function getCardCount() {
  const { data } = await apiClient.get('/cards/count/')
  return data
}

export async function getCard(cardId) {
  const { data } = await apiClient.get(`/cards/${cardId}/`)
  return data
}

export async function deleteCard(cardId) {
  await apiClient.delete(`/cards/${cardId}/`)
}

export async function createCard(payload) {
  const { data } = await apiClient.post('/cards/', payload)
  return data
}
