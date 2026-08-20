import { API_BASE_URL, tokenStorage } from './client'

// http(s)://... -> ws(s)://...
function toWsBase(url) {
  return url.replace(/^http/i, (match) => (match.toLowerCase() === 'https' ? 'wss' : 'ws'))
}

/**
 * meetings 앱의 MeetingConsumer(ws/meetings/<room_code>/)에 연결하는 얇은 래퍼.
 * 백엔드는 세션이 아닌 JWT로 인증하므로, 브라우저 WebSocket이 커스텀 헤더를
 * 보낼 수 없는 제약을 피해 access 토큰을 쿼리스트링(?token=)으로 전달한다.
 */
export class MeetingSocket {
  constructor(roomCode) {
    this.roomCode = roomCode
    this.socket = null
    this.listeners = new Map() // eventType -> Set<handler>
    this._openPromise = null
  }

  on(eventType, handler) {
    if (!this.listeners.has(eventType)) this.listeners.set(eventType, new Set())
    this.listeners.get(eventType).add(handler)
    return () => this.off(eventType, handler)
  }

  off(eventType, handler) {
    this.listeners.get(eventType)?.delete(handler)
  }

  _emit(eventType, payload) {
    this.listeners.get(eventType)?.forEach((handler) => handler(payload))
    this.listeners.get('*')?.forEach((handler) => handler(eventType, payload))
  }

  connect() {
    if (this._openPromise) return this._openPromise

    const token = tokenStorage.getAccess()
    const wsBase = toWsBase(API_BASE_URL)
    const url = `${wsBase}/ws/meetings/${this.roomCode}/?token=${encodeURIComponent(token || '')}`

    this._openPromise = new Promise((resolve, reject) => {
      const socket = new WebSocket(url)
      socket.binaryType = 'arraybuffer'

      socket.onopen = () => resolve(socket)
      socket.onerror = (event) => reject(event)

      socket.onmessage = (event) => {
        if (typeof event.data === 'string') {
          try {
            const data = JSON.parse(event.data)
            this._emit(data.type, data)
          } catch {
            // 텍스트지만 JSON이 아니면 무시
          }
        }
      }

      socket.onclose = () => {
        this._emit('_close')
        this._openPromise = null
      }

      this.socket = socket
    })

    return this._openPromise
  }

  disconnect() {
    this.socket?.close()
    this.socket = null
    this._openPromise = null
  }

  get isOpen() {
    return this.socket?.readyState === WebSocket.OPEN
  }

  sendJson(payload) {
    if (this.isOpen) this.socket.send(JSON.stringify(payload))
  }

  sendBytes(arrayBuffer) {
    if (this.isOpen) this.socket.send(arrayBuffer)
  }

  // --- 편의 메서드 ---

  sendSignal(type, targetId, signalData) {
    this.sendJson({ type, target_id: targetId, ...signalData })
  }

  sendStatusUpdate({ isMicOn, isCameraOn, isSpeaking }) {
    this.sendJson({
      type: 'status_update',
      is_mic_on: isMicOn,
      is_camera_on: isCameraOn,
      is_speaking: isSpeaking,
    })
  }

  sendChatMessage(message, isSpeechCard = false) {
    this.sendJson({ type: 'chat_message', message, is_speech_card: isSpeechCard })
  }
}
