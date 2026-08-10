import germanFlag from '../../assets/img/flags/de.svg'
import japaneseFlag from '../../assets/img/flags/jp.svg'
import chineseFlag from '../../assets/img/flags/cn.svg'
import americanFlag from '../../assets/img/flags/us.svg'

export const personas = [
  {
    id: 'german-manager',
    flag: germanFlag,
    label: '독일 팀장님',
    initialMessage: '일정이 왜 또 늦어지는 거죠? 명확한 이유를 듣고 싶습니다.',
    followUpMessage: '좋습니다, 다음 안건으로 넘어가죠.',
  },
  {
    id: 'japanese-client',
    flag: japaneseFlag,
    label: '일본 클라이언트',
    initialMessage: '전달해 주신 자료는 잘 확인했습니다. 보완 일정도 함께 말씀해 주시겠어요?',
    followUpMessage: '네, 확인했습니다. 다음 내용도 부탁드립니다.',
  },
  {
    id: 'chinese-partner',
    flag: chineseFlag,
    label: '중국 파트너',
    initialMessage: '이번 협력 일정을 중요하게 보고 있습니다. 현재 진행 상황을 알려주세요.',
    followUpMessage: '좋습니다. 다음 논의로 이어가겠습니다.',
  },
  {
    id: 'american-colleague',
    flag: americanFlag,
    label: '미국 동료',
    initialMessage: 'Quick check-in — how is the schedule looking on your end?',
    followUpMessage: 'Sounds good. Let’s move on to the next item.',
  },
]

export const answerExamples = [
  '일정 지연 원인은 A이고, 대안으로 B를 제안드립니다.',
  '3일 지연됐고, 다음 주 화요일까지 마무리하겠습니다.',
  '결론부터 말씀드리면, 예정대로 진행 가능합니다.',
]
