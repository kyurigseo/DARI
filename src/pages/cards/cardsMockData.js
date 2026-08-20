import germanFlag from '../../assets/img/flags/de.svg'
import japaneseFlag from '../../assets/img/flags/jp.svg'
import koreanFlag from '../../assets/img/flags/kr.svg'

export const initialCards = [
  {
    id: 'german-delay',
    persona: '독일 팀장님',
    flag: germanFlag,
    koreanFlag,
    situation: '일정 지연 사유를 설명해야 할 때',
    korean: '일정 지연 원인은 A이고, 대안으로 B를 제안드립니다.',
    translation: 'Die Verzögerung liegt an A, als Alternative schlage ich B vor.',
    language: 'DE',
    languageName: 'Deutsch',
    savedAt: '2일 전',
    tone: 'purple',
  },
  {
    id: 'japanese-confirmation',
    persona: '일본 클라이언트',
    flag: japaneseFlag,
    koreanFlag,
    situation: '완곡하게 재확인 질문할 때',
    korean: '충분히 검토했습니다만, 한 가지만 다시 여쭤봐도 될까요?',
    translation: '十分に検討いたしましたが、一点だけ確認してもよろしいでしょうか。',
    language: '日本',
    languageName: '日本語',
    savedAt: '5일 전',
    tone: 'teal',
  },
]
