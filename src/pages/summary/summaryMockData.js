export const teamMembers = [
  { id: 'jimin', name: '지민', color: '#8454f6' },
  { id: 'anna', name: 'Anna', color: '#12b8a6' },
  { id: 'kim', name: '김', color: '#ff9351' },
  { id: 'soyu', name: '소유', color: '#4c8dff' },
]

export const meetingSummaries = [
  {
    id: 'mock-acme-budget',
    title: 'Q3 예산안 협상 (Acme Corp)',
    date: '8/1',
    aiSummary:
      'Q3 예산안 관련 이견을 조율했으며, 다음 회의 전까지 발표자료 수정본과 계약서 검토 결과를 공유하기로 했어요.',
    actionItems: [
      { id: 'a1', label: '발표자료 수정', done: true, assignee: '지민', due: '8/8' },
      { id: 'a2', label: '계약서 검토', done: false, assignee: null, due: null },
    ],
  },
  {
    id: 'mock-weekly-standup',
    title: '주간 팀 스탠드업',
    date: '7/29',
    aiSummary:
      '각자 진행 중인 작업 현황을 공유했고, 다음 스프린트 우선순위를 함께 정리했어요.',
    actionItems: [
      { id: 'b1', label: '스프린트 보드 정리', done: false, assignee: null, due: null },
    ],
  },
  {
    id: 'mock-berlin-sync',
    title: '베를린 지사 동기화',
    date: '7/25',
    aiSummary:
      '베를린 지사와 시차 문제를 조율하고, 공용 캘린더에 정기 미팅 슬롯을 등록하기로 했어요.',
    actionItems: [
      { id: 'c1', label: '공용 캘린더 슬롯 등록', done: false, assignee: null, due: null },
    ],
  },
]
