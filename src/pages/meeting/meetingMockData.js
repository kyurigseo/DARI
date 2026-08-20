import germanFlag from '../../assets/img/flags/de.svg'
import japaneseFlag from '../../assets/img/flags/jp.svg'

export const initialParticipants = [
  {
    id: 'me',
    name: '나',
    isMe: true,
    isHost: true,
    tzIcon: '☀️',
    localTime: '14:02',
    color: 'var(--color-primary)',
    micOn: false,
    cameraOn: false,
    speaking: false,
  },
  {
    id: 'jimin',
    name: '지민',
    tzIcon: '🌙',
    localTime: '03:02',
    color: '#e0546b',
    micOn: true,
    cameraOn: true,
    speaking: true,
  },
  {
    id: 'anna',
    name: 'Anna',
    tzIcon: '☀️',
    localTime: '10:02',
    color: '#12b8a6',
    micOn: false,
    cameraOn: true,
    speaking: false,
  },
  {
    id: 'yuki',
    name: 'Yuki',
    tzIcon: '🌏',
    localTime: '18:02',
    color: 'var(--color-accent)',
    micOn: false,
    cameraOn: false,
    speaking: false,
  },
]

export const waitingList = [
  { name: '지민', tzIcon: '🌙', localTime: '03:02' },
  { name: 'Anna', tzIcon: '☀️', localTime: '10:02' },
  { name: 'Yuki', tzIcon: '🌏', localTime: '18:02' },
]

export const speechCards = [
  {
    id: 'card-1',
    flag: germanFlag,
    situation: '독일 팀장님 · 일정 지연 사유를 설명해야 할 때',
    korean: '일정 지연 원인은 A이고, 대안으로 B를 제안드립니다.',
    langLabel: 'Deutsch',
    translated: 'Die Verzögerung liegt an A, als Alternative schlage ich B vor.',
  },
  {
    id: 'card-2',
    flag: japaneseFlag,
    situation: '일본 클라이언트 · 완곡하게 재확인 질문할 때',
    korean: '충분히 검토했습니다만, 한 가지만 여쭤봐도 될까요?',
    langLabel: '日本語',
    translated: '十分に検討いたしましたが、一点だけ確認してもよろしいでしょうか。',
  },
]

export const captionScript = [
  {
    original: 'Können wir das Budget nochmal durchgehen?',
    translated: '예산을 다시 검토할 수 있을까요?',
  },
  {
    original: 'Ich denke, Plan B ist realistischer.',
    translated: '제 생각엔 B안이 더 현실적인 것 같아요.',
  },
]

export const initialChatMessages = [
  { id: 'msg-1', sender: '지민', text: '다들 잘 들리시나요?' },
  { id: 'msg-2', sender: 'Anna', text: '예산안 슬라이드 공유해주실 수 있나요?' },
  { id: 'msg-3', sender: '나', text: '네, 지금 화면 공유할게요!' },
]

export const translationLanguages = ['한국어', 'English', '日本語', '中文', 'Deutsch']
