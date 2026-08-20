import { useCallback, useEffect, useRef, useState } from 'react'
import { getMe } from '../../api/auth'
import * as meetingsApi from '../../api/meetings'
import { MeetingSocket } from '../../api/meetingSocket'

const AVATAR_COLORS = ['#8454f6', '#e0546b', '#12b8a6', '#ff9351', '#4f8cff']

// 공개 STUN 서버만 사용 (TURN 서버가 없으면 대칭 NAT/방화벽 환경에서는 연결이 실패할 수 있음)
const ICE_SERVERS = [{ urls: 'stun:stun.l.google.com:19302' }]

function colorFor(index) {
  return AVATAR_COLORS[index % AVATAR_COLORS.length]
}

/**
 * 회의 페이지의 실제 연동 로직을 모아둔 훅.
 * - prejoin API로 대기 중인 참가자 조회
 * - WebSocket(MeetingConsumer)으로 시그널링·상태·채팅·자막 송수신
 * - getUserMedia + RTCPeerConnection 메쉬로 실제 화상/음성 연결
 */
export function useMeetingRoom(roomCode) {
  const [me, setMe] = useState(null)
  const [meetingInfo, setMeetingInfo] = useState(null)
  const [prejoinError, setPrejoinError] = useState('')

  const [joined, setJoined] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [micOn, setMicOn] = useState(true)
  const [cameraOn, setCameraOn] = useState(true)
  const [isScreenSharing, setIsScreenSharing] = useState(false)
  const [localStream, setLocalStream] = useState(null)
  const [participants, setParticipants] = useState([]) // [{id, name, isMe, isHost, micOn, cameraOn, speaking, stream, color}]
  const [captions, setCaptions] = useState([])
  const [chatMessages, setChatMessages] = useState([])
  const [toast, setToast] = useState('')
  const [kicked, setKicked] = useState(false)

  const socketRef = useRef(null)
  const peersRef = useRef(new Map()) // userId -> RTCPeerConnection
  const localStreamRef = useRef(null)
  const meRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const audioStreamRef = useRef(null)
  const audioStreamingActiveRef = useRef(false)
  const audioChunkTimerRef = useRef(null)
  const cameraTrackRef = useRef(null)
  const screenTrackRef = useRef(null)
  const toastTimerRef = useRef(null)

  const showToast = useCallback((message) => {
    setToast(message)
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current)
    toastTimerRef.current = setTimeout(() => setToast(''), 2500)
  }, [])

  // 현재 사용자 정보 + 대기실(prejoin) 정보 조회
  useEffect(() => {
    if (!roomCode) return undefined
    let isMounted = true

    getMe()
      .then((user) => {
        if (isMounted) {
          setMe(user)
          meRef.current = user
        }
      })
      .catch(() => {})

    meetingsApi
      .prejoin(roomCode)
      .then((data) => {
        if (isMounted) setMeetingInfo(data)
      })
      .catch((err) => {
        if (isMounted) {
          setPrejoinError(
            err?.response?.data?.error || '회의 정보를 불러오지 못했어요. 회의 코드를 확인해 주세요.',
          )
        }
      })

    return () => {
      isMounted = false
    }
  }, [roomCode])

  useEffect(() => {
    if (!meetingInfo || !me) return
    setChatMessages(
      (meetingInfo.chat_history || []).map((message) => ({
        id: message.id,
        sender: String(message.sender_id) === String(me.id) ? '나' : message.sender_name,
        text: message.message,
        isSpeechCard: message.is_speech_card,
      })),
    )
    setCaptions(
      (meetingInfo.transcript_history || []).map((transcript) => ({
        id: transcript.id,
        speakerId: transcript.speaker_id,
        speakerName: transcript.speaker_name,
        original: transcript.original_text,
        translations: transcript.translations,
      })),
    )
  }, [meetingInfo, me])

  const participantsRef = useRef([])

  const upsertParticipant = useCallback((userId, patch) => {
    setParticipants((prev) => {
      const idx = prev.findIndex((p) => p.id === userId)
      if (idx === -1) {
        return [
          ...prev,
          {
            id: userId,
            name: patch.name || `참가자 ${userId}`,
            isMe: meRef.current && String(userId) === String(meRef.current.id),
            isHost: false,
            micOn: true,
            cameraOn: true,
            speaking: false,
            stream: null,
            color: colorFor(prev.length),
            ...patch,
          },
        ]
      }
      const next = [...prev]
      next[idx] = { ...next[idx], ...patch }
      return next
    })
  }, [])

  useEffect(() => {
    participantsRef.current = participants
  }, [participants])

  const removeParticipant = useCallback((userId) => {
    setParticipants((prev) => prev.filter((p) => p.id !== userId))
    const pc = peersRef.current.get(userId)
    if (pc) {
      pc.close()
      peersRef.current.delete(userId)
    }
  }, [])

  const createPeerConnection = useCallback(
    (remoteUserId) => {
      const existing = peersRef.current.get(remoteUserId)
      if (existing) return existing

      const pc = new RTCPeerConnection({ iceServers: ICE_SERVERS })

      localStreamRef.current?.getTracks().forEach((track) => {
        pc.addTrack(track, localStreamRef.current)
      })

      pc.onicecandidate = (event) => {
        if (event.candidate) {
          socketRef.current?.sendSignal('candidate', remoteUserId, { candidate: event.candidate })
        }
      }

      pc.ontrack = (event) => {
        upsertParticipant(remoteUserId, { stream: event.streams[0] })
      }

      pc.onconnectionstatechange = () => {
        if (['failed', 'closed', 'disconnected'].includes(pc.connectionState)) {
          peersRef.current.delete(remoteUserId)
        }
      }

      peersRef.current.set(remoteUserId, pc)
      return pc
    },
    [upsertParticipant],
  )

  const sendOfferTo = useCallback(
    async (remoteUserId) => {
      const pc = createPeerConnection(remoteUserId)
      const offer = await pc.createOffer()
      await pc.setLocalDescription(offer)
      socketRef.current?.sendSignal('offer', remoteUserId, { sdp: offer })
    },
    [createPeerConnection],
  )

  // 오디오를 잘게 잘라 서버로 전송 -> STT/번역 파이프라인이 자막을 생성
  //
  // 주의: MediaRecorder.start(timeslice)로 만든 청크는 첫 조각에만 WebM 헤더가 있고
  // 이후 조각들은 헤더 없는 continuation cluster라 단독으로는 디코딩이 안 된다.
  // 백엔드가 각 청크를 1:1로 즉시 Whisper에 넘기도록 바뀌었으므로, 매번 완전한
  // WebM 헤더를 가진 독립 파일이 되도록 recorder를 주기적으로 stop() 후 다시
  // start()해서 청크를 만든다.
  const AUDIO_CHUNK_MS = 3500

  const recordNextAudioChunk = useCallback(() => {
    if (!audioStreamingActiveRef.current || !audioStreamRef.current) return
    try {
      const recorder = new MediaRecorder(audioStreamRef.current, { mimeType: 'audio/webm;codecs=opus' })

      recorder.ondataavailable = async (event) => {
        if (event.data && event.data.size > 0 && socketRef.current?.isOpen) {
          const buffer = await event.data.arrayBuffer()
          socketRef.current.sendBytes(buffer)
        }
      }

      recorder.onstop = () => {
        // 아직 스트리밍 중이면 곧바로 다음 독립 청크 녹음을 시작한다.
        if (audioStreamingActiveRef.current) recordNextAudioChunk()
      }

      recorder.start()
      mediaRecorderRef.current = recorder

      audioChunkTimerRef.current = setTimeout(() => {
        if (recorder.state !== 'inactive') recorder.stop()
      }, AUDIO_CHUNK_MS)
    } catch (err) {
      // MediaRecorder 미지원 브라우저 등 - 자막 없이 화상/음성은 정상 동작
      console.warn('오디오 스트리밍을 시작하지 못했습니다.', err)
    }
  }, [])

  const startAudioStreaming = useCallback(
    (stream) => {
      if (!stream.getAudioTracks().length) return
      audioStreamRef.current = new MediaStream(stream.getAudioTracks())
      audioStreamingActiveRef.current = true
      recordNextAudioChunk()
    },
    [recordNextAudioChunk],
  )

  const stopAudioStreaming = useCallback(() => {
    audioStreamingActiveRef.current = false
    clearTimeout(audioChunkTimerRef.current)
    audioChunkTimerRef.current = null
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.onstop = null
      mediaRecorderRef.current.stop()
    }
    mediaRecorderRef.current = null
    audioStreamRef.current = null
  }, [])

  const handleSocketMessage = useCallback(
    (eventType, data) => {
      const myId = meRef.current?.id

      switch (eventType) {
        case 'user_joined': {
          if (String(data.user_id) === String(myId)) return
          upsertParticipant(data.user_id, { name: data.username })
          // 이미 방에 있던 나는, 새로 들어온 사람에게 오퍼를 보내지 않는다.
          // (새로 들어온 쪽이 기존 참가자 전원에게 오퍼를 보내는 규칙)
          showToast(`${data.username}님이 입장했어요`)
          break
        }
        case 'user_left': {
          const target = participantsRef.current.find((p) => p.id === data.user_id)
          removeParticipant(data.user_id)
          if (target) showToast(`${target.name}님이 퇴장했어요`)
          break
        }
        case 'status_changed': {
          // 서버는 변경되지 않은 필드를 null로 보낼 수 있다(부분 업데이트).
          // null/undefined인 필드는 무시해서 다른 상태(예: 카메라)가 실수로
          // 덮어써지지 않도록 한다.
          const patch = {}
          if (data.is_mic_on !== null && data.is_mic_on !== undefined) patch.micOn = data.is_mic_on
          if (data.is_camera_on !== null && data.is_camera_on !== undefined) patch.cameraOn = data.is_camera_on
          if (data.is_speaking !== null && data.is_speaking !== undefined) patch.speaking = data.is_speaking
          upsertParticipant(data.user_id, patch)
          break
        }
        case 'chat': {
          setChatMessages((prev) => [
            ...prev,
            {
              id: `${data.sender_id}-${Date.now()}`,
              sender: String(data.sender_id) === String(myId) ? '나' : data.sender_name,
              text: data.message,
              isSpeechCard: data.is_speech_card,
            },
          ])
          break
        }
        case 'subtitle': {
          setCaptions((prev) =>
            [
              ...prev,
              {
                id: `${data.speaker_id}-${Date.now()}`,
                speakerId: data.speaker_id,
                speakerName: data.speaker_name,
                original: data.original_text,
                translations: data.translations,
              },
            ].slice(-20),
          )
          break
        }
        case 'offer': {
          if (String(data.target_id) !== String(myId)) return
          ;(async () => {
            const pc = createPeerConnection(data.sender_id)
            await pc.setRemoteDescription(new RTCSessionDescription(data.sdp))
            const answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            socketRef.current?.sendSignal('answer', data.sender_id, { sdp: answer })
          })()
          break
        }
        case 'answer': {
          if (String(data.target_id) !== String(myId)) return
          const pc = peersRef.current.get(data.sender_id)
          pc?.setRemoteDescription(new RTCSessionDescription(data.sdp))
          break
        }
        case 'candidate': {
          if (String(data.target_id) !== String(myId)) return
          const pc = peersRef.current.get(data.sender_id)
          if (pc && data.candidate) {
            pc.addIceCandidate(new RTCIceCandidate(data.candidate)).catch(() => {})
          }
          break
        }
        case 'kicked': {
          setKicked(true)
          break
        }
        default:
          break
      }
    },
    [createPeerConnection, removeParticipant, showToast, upsertParticipant],
  )

  const cleanupCall = useCallback(() => {
    stopAudioStreaming()

    localStreamRef.current?.getTracks().forEach((track) => track.stop())
    if (screenTrackRef.current) {
      screenTrackRef.current.onended = null
      screenTrackRef.current.stop()
    }
    cameraTrackRef.current?.stop()
    screenTrackRef.current = null
    cameraTrackRef.current = null
    setIsScreenSharing(false)
    localStreamRef.current = null
    setLocalStream(null)

    peersRef.current.forEach((pc) => pc.close())
    peersRef.current.clear()

    socketRef.current?.disconnect()
    socketRef.current = null

    setParticipants([])
    setCaptions([])
  }, [stopAudioStreaming])

  const join = useCallback(async () => {
    if (!roomCode || connecting || joined) return
    setConnecting(true)
    setKicked(false)

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true })
      stream.getAudioTracks().forEach((track) => {
        track.enabled = micOn
      })
      stream.getVideoTracks().forEach((track) => {
        track.enabled = cameraOn
      })
      localStreamRef.current = stream
      cameraTrackRef.current = stream.getVideoTracks()[0] || null
      setLocalStream(stream)

      const existingParticipants = meetingInfo?.participants || []

      const socket = new MeetingSocket(roomCode)
      socketRef.current = socket
      socket.on('*', handleSocketMessage)
      await socket.connect()

      if (meRef.current) {
        upsertParticipant(meRef.current.id, {
          name: meRef.current.username,
          isMe: true,
          isHost: meetingInfo?.host_id ? meetingInfo.host_id === meRef.current.id : true,
          micOn,
          cameraOn,
          stream,
        })
      }

      // 이미 접속 중이던 참가자들에게는 내가 먼저 오퍼를 보낸다.
      existingParticipants
        .filter((p) => !meRef.current || String(p.user) !== String(meRef.current.id))
        .forEach((p) => {
          upsertParticipant(p.user, {
            name: p.username,
            isHost: p.is_host,
            micOn: p.is_mic_on,
            cameraOn: p.is_camera_on,
          })
          sendOfferTo(p.user)
        })

      socket.sendStatusUpdate({ isMicOn: micOn, isCameraOn: cameraOn, isSpeaking: false })
      startAudioStreaming(stream)

      setJoined(true)
      showToast('회의에 참가했어요 🎉')
    } catch (err) {
      showToast(
        err?.name === 'NotAllowedError'
          ? '카메라/마이크 권한을 허용해 주세요.'
          : '회의 참가에 실패했어요. 잠시 후 다시 시도해 주세요.',
      )
      cleanupCall()
    } finally {
      setConnecting(false)
    }
  }, [
    roomCode,
    connecting,
    joined,
    micOn,
    cameraOn,
    meetingInfo,
    handleSocketMessage,
    sendOfferTo,
    startAudioStreaming,
    upsertParticipant,
    showToast,
    cleanupCall,
  ])

  const leave = useCallback(() => {
    cleanupCall()
    setJoined(false)
  }, [cleanupCall])

  useEffect(() => {
    if (kicked) {
      showToast('호스트가 회의에서 내보냈어요')
      cleanupCall()
      setJoined(false)
    }
  }, [kicked, cleanupCall, showToast])

  const toggleMic = useCallback(() => {
    setMicOn((prev) => {
      const next = !prev
      localStreamRef.current?.getAudioTracks().forEach((track) => {
        track.enabled = next
      })
      // 서버가 받은 필드만 부분 반영/브로드캐스트하므로, 현재 알고 있는 두 상태를
      // 항상 같이 보내 다른 참가자 화면에서 카메라 상태가 유실되지 않도록 한다.
      socketRef.current?.sendStatusUpdate({ isMicOn: next, isCameraOn: cameraOn })
      if (meRef.current) upsertParticipant(meRef.current.id, { micOn: next })
      return next
    })
  }, [cameraOn, upsertParticipant])

  const toggleCamera = useCallback(() => {
    setCameraOn((prev) => {
      const next = !prev
      const cameraTracks = screenTrackRef.current
        ? [cameraTrackRef.current].filter(Boolean)
        : localStreamRef.current?.getVideoTracks() || []
      cameraTracks.forEach((track) => {
        track.enabled = next
      })
      socketRef.current?.sendStatusUpdate({ isMicOn: micOn, isCameraOn: next })
      if (meRef.current) upsertParticipant(meRef.current.id, { cameraOn: next })
      return next
    })
  }, [micOn, upsertParticipant])

  const stopScreenShare = useCallback(async () => {
    const cameraTrack = cameraTrackRef.current
    const screenTrack = screenTrackRef.current
    if (!screenTrack) return

    peersRef.current.forEach((pc) => {
      const sender = pc.getSenders().find((item) => item.track?.kind === 'video')
      sender?.replaceTrack(cameraTrack || null)
    })

    const currentStream = localStreamRef.current
    const audioTracks = currentStream?.getAudioTracks() || []
    const restoredStream = new MediaStream([...audioTracks, ...(cameraTrack ? [cameraTrack] : [])])
    localStreamRef.current = restoredStream
    setLocalStream(restoredStream)
    screenTrack.onended = null
    screenTrack.stop()
    screenTrackRef.current = null
    setIsScreenSharing(false)
    if (meRef.current) upsertParticipant(meRef.current.id, { stream: restoredStream })
  }, [upsertParticipant])

  const toggleScreenShare = useCallback(async () => {
    if (screenTrackRef.current) {
      await stopScreenShare()
      return
    }

    try {
      const displayStream = await navigator.mediaDevices.getDisplayMedia({ video: true })
      const screenTrack = displayStream.getVideoTracks()[0]
      if (!screenTrack) return

      screenTrackRef.current = screenTrack
      peersRef.current.forEach((pc) => {
        const sender = pc.getSenders().find((item) => item.track?.kind === 'video')
        sender?.replaceTrack(screenTrack)
      })

      const audioTracks = localStreamRef.current?.getAudioTracks() || []
      const sharedStream = new MediaStream([...audioTracks, screenTrack])
      localStreamRef.current = sharedStream
      setLocalStream(sharedStream)
      setIsScreenSharing(true)
      if (meRef.current) upsertParticipant(meRef.current.id, { stream: sharedStream, cameraOn: true })
      screenTrack.onended = () => {
        stopScreenShare()
      }
    } catch (err) {
      if (err?.name === 'NotAllowedError') showToast('화면 공유가 취소되었어요.')
      else showToast('화면 공유를 시작하지 못했어요.')
    }
  }, [showToast, stopScreenShare, upsertParticipant])

  const sendChat = useCallback((text, isSpeechCard = false) => {
    if (!text.trim()) return
    socketRef.current?.sendChatMessage(text.trim(), isSpeechCard)
  }, [])

  const invite = useCallback(
    async (username) => {
      if (!roomCode || !username.trim()) return
      try {
        const data = await meetingsApi.manageParticipants(roomCode, { username: username.trim() })
        if (data.participant) {
          upsertParticipant(data.participant.user, {
            name: data.participant.username,
            isHost: data.participant.is_host,
            micOn: data.participant.is_mic_on,
            cameraOn: data.participant.is_camera_on,
          })
        }
        showToast(`${username}님을 초대했어요`)
      } catch (err) {
        showToast(err?.response?.data?.error || '초대에 실패했어요')
      }
    },
    [roomCode, showToast, upsertParticipant],
  )

  const kick = useCallback(
    async (userId) => {
      if (!roomCode) return
      try {
        await meetingsApi.kickParticipant(roomCode, userId)
        const target = participants.find((p) => p.id === userId)
        removeParticipant(userId)
        if (target) showToast(`${target.name}님을 내보냈어요`)
      } catch (err) {
        showToast(err?.response?.data?.error || '내보내기에 실패했어요')
      }
    },
    [roomCode, participants, removeParticipant, showToast],
  )

  const endMeeting = useCallback(async () => {
    if (!roomCode) return
    try {
      await meetingsApi.endMeeting(roomCode)
      leave()
      return true
    } catch (err) {
      showToast(err?.response?.data?.error || '회의 종료에 실패했어요')
      return false
    }
  }, [roomCode, showToast, leave])

  // 언마운트 시 정리
  useEffect(() => () => cleanupCall(), [cleanupCall])

  return {
    me,
    meetingInfo,
    prejoinError,
    joined,
    connecting,
    micOn,
    cameraOn,
    isScreenSharing,
    localStream,
    participants,
    captions,
    chatMessages,
    toast,
    join,
    leave,
    toggleMic,
    toggleCamera,
    toggleScreenShare,
    sendChat,
    invite,
    kick,
    endMeeting,
  }
}