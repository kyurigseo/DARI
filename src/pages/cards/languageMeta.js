import deFlag from '../../assets/img/flags/de.svg'
import jpFlag from '../../assets/img/flags/jp.svg'
import krFlag from '../../assets/img/flags/kr.svg'
import cnFlag from '../../assets/img/flags/cn.svg'
import usFlag from '../../assets/img/flags/us.svg'

const LANGUAGE_META = {
  de: { flag: deFlag, label: 'DE', name: 'Deutsch', tone: 'purple' },
  ja: { flag: jpFlag, label: '日本', name: '日本語', tone: 'teal' },
  jp: { flag: jpFlag, label: '日本', name: '日本語', tone: 'teal' },
  zh: { flag: cnFlag, label: 'CN', name: '中文', tone: 'orange' },
  cn: { flag: cnFlag, label: 'CN', name: '中文', tone: 'orange' },
  en: { flag: usFlag, label: 'EN', name: 'English', tone: 'blue' },
  us: { flag: usFlag, label: 'EN', name: 'English', tone: 'blue' },
}

export function getLanguageMeta(languageCode) {
  return LANGUAGE_META[(languageCode || '').toLowerCase()] || {
    flag: usFlag,
    label: (languageCode || '').toUpperCase(),
    name: languageCode || '',
    tone: 'blue',
  }
}

export const koreanFlag = krFlag

export function formatRelativeTime(isoString) {
  if (!isoString) return ''
  const now = new Date()
  const date = new Date(isoString)
  const diffMs = now - date
  const diffMin = Math.floor(diffMs / 60000)

  if (diffMin < 1) return '방금 전'
  if (diffMin < 60) return `${diffMin}분 전`
  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `${diffHour}시간 전`
  const diffDay = Math.floor(diffHour / 24)
  return `${diffDay}일 전`
}
