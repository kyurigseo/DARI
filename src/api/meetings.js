import { meetingsClient } from './client'

export async function createMeeting(payload) {
  const { data } = await meetingsClient.post('/meetings/', payload)
  return data
}

export async function getSpeechCards() {
  const { data } = await meetingsClient.get('/meetings/speech-cards/')
  return data
}

export async function prejoin(roomCode) {
  const { data } = await meetingsClient.get(`/meetings/${roomCode}/prejoin/`)
  return data
}

export async function getMediaToken(roomCode) {
  const { data } = await meetingsClient.get(`/meetings/${roomCode}/token/`)
  return data
}

export async function manageParticipants(roomCode, payload) {
  const { data } = await meetingsClient.post(`/meetings/${roomCode}/participants/`, payload)
  return data
}

export async function kickParticipant(roomCode, userId) {
  const { data } = await meetingsClient.post(`/meetings/${roomCode}/kick/`, { user_id: userId })
  return data
}

export async function endMeeting(roomCode) {
  const { data } = await meetingsClient.post(`/meetings/${roomCode}/end/`)
  return data
}

export async function getSummaryTabs() {
  const { data } = await meetingsClient.get('/meetings/summary-tabs/')
  return data
}

export async function getMeetingReport(roomCode) {
  const { data } = await meetingsClient.get(`/meetings/${roomCode}/report/`)
  return data
}

export async function getMemos(roomCode) {
  const { data } = await meetingsClient.get(`/meetings/${roomCode}/memos/`)
  return data
}

export async function createMemo(roomCode, content) {
  const { data } = await meetingsClient.post(`/meetings/${roomCode}/memos/`, { content })
  return data
}

export async function deleteMemo(memoId) {
  await meetingsClient.delete(`/meetings/memos/${memoId}/`)
}

export async function updateActionItem(itemId, payload) {
  const { data } = await meetingsClient.patch(`/meetings/action-items/${itemId}/`, payload)
  return data
}

export async function getShareText(roomCode) {
  const { data } = await meetingsClient.get(`/meetings/${roomCode}/share-text/`)
  return data
}

export async function sendReportEmail(roomCode, payload) {
  const { data } = await meetingsClient.post(`/meetings/${roomCode}/send-email/`, payload)
  return data
}

export async function getInvitations() {
  const { data } = await meetingsClient.get('/meetings/invitations/')
  return data
}

export async function respondInvitation(meetingId, action) {
  const { data } = await meetingsClient.post(`/meetings/invitations/${meetingId}/respond/`, { action })
  return data
}
