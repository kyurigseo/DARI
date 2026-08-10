const makeRow = (...segments) => {
  const row = []

  segments.forEach(([status, length]) => {
    row.push(...Array.from({ length }, () => status))
  })

  return row
}

export const recentParticipants = [
  { name: '지민', percent: 83, badge: '새벽 5/6', tone: 'red' },
  { name: 'A', percent: 17, badge: '주간 1/6', tone: 'teal' },
  { name: 'Y', percent: 50, badge: '저녁 3/6', tone: 'orange' },
]

export const timeLabels = Array.from(
  { length: 12 },
  (_, index) => `${String(index * 2).padStart(2, '0')}:00`,
)

export const availabilityStatusLabels = {
  comfortable: '편한 시간',
  normal: '보통',
  uncomfortable: '불편한 시간',
}

export const initialAvailability = {
  me: makeRow(
    ['uncomfortable', 14],
    ['normal', 4],
    ['comfortable', 18],
    ['normal', 6],
    ['uncomfortable', 6],
  ),
  jimin: makeRow(
    ['comfortable', 10],
    ['normal', 6],
    ['uncomfortable', 20],
    ['normal', 5],
    ['comfortable', 7],
  ),
  anna: makeRow(
    ['normal', 2],
    ['uncomfortable', 20],
    ['normal', 4],
    ['comfortable', 18],
    ['normal', 4],
  ),
  yuki: makeRow(
    ['uncomfortable', 6],
    ['normal', 4],
    ['comfortable', 18],
    ['normal', 6],
    ['uncomfortable', 14],
  ),
}

export const localTimes = [
  { id: 'me', name: '나', time: '13:00', status: 'comfortable' },
  { id: 'jimin', name: '지민', time: '02:00', status: 'uncomfortable' },
  { id: 'anna', name: 'Anna', time: '09:00', status: 'comfortable' },
  { id: 'yuki', name: 'Yuki', time: '17:00', status: 'comfortable' },
]

// TODO: 최근 참여 통계, timezone, availability 데이터는 관련 API 준비 후 교체합니다.
