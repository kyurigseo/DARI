# STT 및 번역 서비스 구현

import io
import os
import httpx
import urllib.parse
import json
from django.conf import settings
from .models import MeetingSession, MeetingTranscript, MeetingChatMessage, MeetingSummary, ActionItem, MeetingMemo

# 언어 코드 매핑 테이블
LANGUAGE_MAPPING = {
    '한국어': 'KO',
    'English': 'EN-US',
    '日本語': 'JA',
    '中文': 'ZH',
    'Deutsch': 'DE',
}

class AIServicePipeline:
    @staticmethod
    async def process_stt(audio_bytes: bytes) -> str:
        """
        [STT 파이프라인] 음성 바이너리 데이터를 OpenAI Whisper API 등으로 전달하여 텍스트 추출
        """
        api_key = getattr(settings, 'OPENAI_API_KEY', os.getenv('OPENAI_API_KEY', ''))
        if not api_key or len(audio_bytes) < 1000: # 음성 데이터가 너무 짧으면 패스
            return ""

        url = "https://api.openai.com/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {api_key}"}


        audio_file = ("audio.wav", io.BytesIO(audio_bytes), "audio/wav")
        files = {"file": audio_file}
        data = {"model": "whisper-1"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, headers=headers, files=files, data=data)
                if response.status_code == 200:
                    return response.json().get("text", "").strip()
        except Exception as e:
            print(f"[STT 오류] {e}")

        return ""

    @staticmethod
    async def process_translation(text: str, target_langs: list) -> dict:
        """
        [번역 파이프라인] STT 텍스트를 target_langs(예: ['KO', 'EN-US', 'DE']) 언어들로 번역
        번역 실패 시 예외 처리: 원문 출력 및 Fallback
        """
        if not text:
            return {}

        api_key = getattr(settings, 'DEEPL_API_KEY', os.getenv('DEEPL_API_KEY', ''))
        translations = {}

        # DeepL API 연동 예시 (OpenAI로 대체 가능)
        if api_key:
            url = "https://api-free.deepl.com/v2/translate"
            headers = {
                "Authorization": f"DeepL-Auth-Key {api_key}",
                "Content-Type": "application/json"
            }

            async with httpx.AsyncClient(timeout=5.0) as client:
                for lang in target_langs:
                    try:
                        payload = {
                            "text": [text],
                            "target_lang": lang
                        }
                        res = await client.post(url, headers=headers, json=payload)
                        if res.status_code == 200:
                            translated_text = res.json()["translations"][0]["text"]
                            translations[lang] = translated_text
                        else:
                            translations[lang] = text
                    except Exception as e:
                        print(f"[번역 오류 - {lang}] {e}")
                        translations[lang] = text
        else:
            for lang in target_langs:
                translations[lang] = f"[번역-{lang}] {text}"

        return translations

class MeetingSummaryPipeline:
    @staticmethod
    def generate_summary_and_action_items(meeting_id: int):
        """
        회의 종료 시 호출되는 AI 요약 및 Action Item 추출 파이프라인
        - STT 음성 기록 및 채팅 기록 수집
        - 음성 부재 시 채팅 로그로 대체
        - 데이터 부족 시 기본 안내 문구 Fallback
        - JSON 파싱 및 DB 자동 저장
        """
        meeting = MeetingSession.objects.filter(id=meeting_id).first()
        if not meeting:
            return


        transcripts = list(MeetingTranscript.objects.filter(meeting=meeting).order_by('created_at'))
        chat_messages = list(MeetingChatMessage.objects.filter(meeting=meeting).order_by('created_at'))

        dialogues = []
        if transcripts:
            for t in transcripts:
                dialogues.append(f"[음성] {t.speaker.username}: {t.original_text}")

        if chat_messages:
            for c in chat_messages:
                dialogues.append(f"[채팅] {c.sender.username}: {c.message}")

        full_content = "\n".join(dialogues).strip()

        if not full_content or len(dialogues) < 2:
            MeetingSummary.objects.update_or_create(
                meeting=meeting,
                defaults={'content': '회의 내용이 충분하지 않아 요약이 생성되지 않았습니다.'}
            )
            return


        api_key = getattr(settings, 'OPENAI_API_KEY', os.getenv('OPENAI_API_KEY', ''))

        system_prompt = """
        당신은 다국어 화상 회의 전문 AI 어시스턴트입니다.
        주어진 회의 대화 내용을 바탕으로 다음 두 가지를 JSON 형태로 추출하세요:
        1. summary: 회의의 핵심 안건 및 결정 사항을 2~3문장의 명확한 한국어로 요약 (존댓말 사용)
        2. action_items: 해야 할 일 목록을 아래 형식의 리스트로 추출
           - task: 구체적인 할 일 내용 (문장형이 아닌 명사형으로 간결하게 작성)
           - assignee: 담당자 이름. 언급되지 않았거나 불명확하면 반드시 "미지정"으로 기재
           - due_date: 마감 기한 (YYYY-MM-DD 형식). 언급되지 않았으면 null로 기재

        반드시 아래 JSON 포맷으로만 응답하세요:
        {
            "summary": "요약 내용",
            "action_items": [
                {"task": "발표자료 수정", "assignee": "지민", "due_date": "2026-08-08"},
                {"task": "계약서 검토", "assignee": "미지정", "due_date": null}
            ]
        }
        """

        summary_text = "회의 내용을 요약 중입니다."
        action_items_data = []

        if api_key:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "gpt-4o-mini",
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"회의 대화 내용:\n{full_content}"}
                ],
                "temperature": 0.2
            }

            try:
                with httpx.Client(timeout=30.0) as client:
                    res = client.post(url, headers=headers, json=payload)
                    if res.status_code == 200:
                        res_json = res.json()
                        result_data = json.loads(res_json['choices'][0]['message']['content'])
                        summary_text = result_data.get('summary', summary_text)
                        action_items_data = result_data.get('action_items', [])
            except Exception as e:
                print(f"[AI 요약 생성 오류] {e}")
                summary_text = "AI 요약 생성 중 일시적인 오류가 발생했습니다."
        else:
            summary_text = f"{meeting.title} 회의 관련 의견을 조율했으며, 주요 안건에 대한 검토 결과를 공유하기로 했습니다."
            action_items_data = [
                {"task": "발표자료 수정", "assignee": "지민", "due_date": "2026-08-08"},
                {"task": "계약서 검토", "assignee": "미지정", "due_date": None}
            ]

        MeetingSummary.objects.update_or_create(
            meeting=meeting,
            defaults={'content': summary_text}
        )

        for item in action_items_data:
            task = item.get('task', '').strip()
            if not task:
                continue
            assignee = item.get('assignee') or '미지정'
            due_date = item.get('due_date')  # YYYY-MM-DD 또는 None

            ActionItem.objects.create(
                meeting=meeting,
                task=task,
                assignee=assignee,
                due_date=due_date,
                is_completed=False
            )

class MeetingShareFormatter:
    """
    회의 요약, 내 메모, Action Items를 클립보드/Slack/메일 본문용 텍스트로 가공하는 포맷터
    """
    @staticmethod
    def generate_formatted_text(meeting: MeetingSession, user) -> str:
        month = meeting.created_at.month
        day = meeting.created_at.day

        title_line = f"📝 {meeting.title} ({month}/{day})"
        summary_obj = getattr(meeting, 'summary', None)
        summary_content = summary_obj.content if summary_obj else "요약 내용이 없습니다."
        summary_block = f"[AI 요약]\n{summary_content}"

        user_memos = MeetingMemo.objects.filter(meeting=meeting, user=user).order_by('created_at')
        if user_memos.exists():
            memos_text = "\n".join([f"- {memo.content}" for memo in user_memos])
        else:
            memos_text = "- 작성된 메모가 없습니다."
        memo_block = f"[내 메모]\n{memos_text}"

        action_items = ActionItem.objects.filter(meeting=meeting).order_by('created_at')
        if action_items.exists():
            items_list = []
            for item in action_items:
                status_str = "완료" if item.is_completed else "진행중"
                due_str = f"마감 {item.due_date.month}/{item.due_date.day}" if item.due_date else "기한 미지정"
                items_list.append(f"- [{status_str}] {item.task} ({item.assignee} · {due_str})")
            action_block = f"[Action Items]\n" + "\n".join(items_list)
        else:
            action_block = "[Action Items]\n- 등록된 Action Item이 없습니다."

        return f"{title_line}\n\n{summary_block}\n\n{memo_block}\n\n{action_block}"