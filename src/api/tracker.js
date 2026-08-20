import apiClient from './client'

export async function getLatestAlert() {
  const { data } = await apiClient.get('/tracker/alerts/latest/')
  return data
}

export async function getParticipationSummary(participantIds = []) {
  const { data } = await apiClient.get('/tracker/participation/summary/', {
    params: participantIds.length ? { participant_ids: participantIds.join(',') } : {},
  })
  return data
}

export async function getHeatmap(participantIds = []) {
  const { data } = await apiClient.get('/tracker/heatmap/', {
    params: participantIds.length ? { participant_ids: participantIds.join(',') } : {},
  })
  return data
}

export async function updateMyHeatmapSlot({ weekday, halfHourIndex, status }) {
  const { data } = await apiClient.patch('/tracker/heatmap/me/', {
    weekday,
    half_hour_index: halfHourIndex,
    status,
  })
  return data
}

export async function getRecommendation(participantIds) {
  const { data } = await apiClient.post('/tracker/recommendations/', {
    participant_ids: participantIds,
  })
  return data
}

export async function confirmMeeting({ title, weekday, halfHourIndex, participantIds }) {
  const { data } = await apiClient.post('/tracker/meetings/confirm/', {
    title,
    weekday,
    half_hour_index: halfHourIndex,
    participant_ids: participantIds,
  })
  return data
}
