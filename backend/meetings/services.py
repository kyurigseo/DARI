# STT 및 번역 서비스 구현

import io
import os
import httpx
from django.conf import settings

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