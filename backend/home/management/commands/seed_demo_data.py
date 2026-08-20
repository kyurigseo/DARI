from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from cards.models import Card
from meetings.models import (
    ActionItem,
    MeetingChatMessage,
    MeetingMemo,
    MeetingParticipant,
    MeetingSession,
    MeetingSummary,
    MeetingTranscript,
)
from tracker.models import AvailabilitySlot, ParticipationRecord


DEMO_PASSWORD = "DariDemo123!"


class Command(BaseCommand):
    help = "로컬 Figma 검수용 demo 사용자와 회의 데이터를 멱등하게 생성합니다."

    def add_arguments(self, parser):
        parser.add_argument("--host-username", required=True)

    def handle(self, *args, **options):
        if not settings.DARI_DEMO_MODE:
            raise CommandError("DARI_DEMO_MODE=true인 로컬 환경에서만 실행할 수 있습니다.")

        User = get_user_model()
        host_username = options["host_username"]
        host, host_created = User.objects.get_or_create(
            username=host_username,
            defaults={
                "email": f"{host_username}.demo@dari.local",
                "country": "KR",
                "role": "MANAGER",
            },
        )
        if host_created:
            host.set_password(DEMO_PASSWORD)
            host.save()

        demo_specs = [
            ("지민", "DE", "jimin.demo@dari.local"),
            ("Anna", "US", "anna.demo@dari.local"),
            ("Yuki", "JP", "yuki.demo@dari.local"),
        ]
        users = [host]
        for username, country, email in demo_specs:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"email": email, "country": country, "role": "STAFF"},
            )
            user.email = email
            user.country = country
            user.role = "STAFF"
            if created or not user.has_usable_password():
                user.set_password(DEMO_PASSWORD)
            user.save()
            users.append(user)

        if not host.country:
            host.country = "KR"
            host.save(update_fields=["country"])

        meeting, _ = MeetingSession.objects.update_or_create(
            room_code="demo-acme-negotiation",
            defaults={"title": "Acme Corp 협상", "host": host, "status": "WAITING"},
        )
        for index, user in enumerate(users):
            MeetingParticipant.objects.update_or_create(
                meeting=meeting,
                user=user,
                defaults={
                    "is_host": user == host,
                    "is_active": True,
                    "is_mic_on": index != 1,
                    "is_camera_on": False,
                    "local_time_zone": ["Asia/Seoul", "Europe/Berlin", "America/New_York", "Asia/Tokyo"][index],
                },
            )

        demo_chats = [
            (users[1], "다들 잘 들리시나요?"),
            (users[2], "예산안 슬라이드 공유해주실 수 있나요?"),
            (host, "네, 지금 화면 공유할게요!"),
        ]
        MeetingChatMessage.objects.filter(meeting=meeting).delete()
        for sender, message in demo_chats:
            MeetingChatMessage.objects.create(meeting=meeting, sender=sender, message=message)

        MeetingTranscript.objects.update_or_create(
            meeting=meeting,
            speaker=users[1],
            original_text="Können wir das Budget nochmal durchgehen?",
            defaults={
                "speaker_lang": "DE",
                "translations": {
                    "KO": "예산을 다시 검토할 수 있을까요?",
                    "EN-US": "Could we review the budget again?",
                    "JA": "予算をもう一度確認できますか？",
                    "ZH": "我们可以再审查一下预算吗？",
                    "DE": "Können wir das Budget nochmal durchgehen?",
                },
            },
        )

        card_specs = [
            ("독일 팀장님", "일정 지연 사유를 설명할 때", "핵심 원인을 먼저 설명드리고 대안을 제시하겠습니다.", "Ich erläutere zuerst die Hauptursache und schlage dann eine Alternative vor.", "de"),
            ("일본 클라이언트", "정중하게 재검토를 요청할 때", "가능하시다면 이 안을 다시 한번 검토해주시겠어요?", "可能でしたら、この案をもう一度ご検討いただけますか。", "ja"),
            ("미국 동료", "다음 행동을 제안할 때", "다음 단계와 담당자를 지금 정해보면 어떨까요?", "How about we decide the next steps and owners now?", "en"),
        ]
        for partner, situation, ko, translated, language in card_specs:
            Card.objects.update_or_create(
                owner=host,
                partner_tag=partner,
                situation_label=situation,
                defaults={
                    "text_ko": ko,
                    "text_translated": translated,
                    "language_code": language,
                    "explanation": "핵심을 먼저 전달하는 표현입니다.",
                },
            )

        timezones = ["Asia/Seoul", "Europe/Berlin", "America/New_York", "Asia/Tokyo"]
        comfortable_ranges = [(0, 17), (14, 31), (26, 43), (0, 17)]
        for user, (start, end) in zip(users, comfortable_ranges):
            for weekday in range(7):
                for slot_index in range(48):
                    status = AvailabilitySlot.UNCOMFORTABLE
                    if start <= slot_index <= end:
                        status = AvailabilitySlot.COMFORTABLE
                    elif start - 3 <= slot_index <= end + 3:
                        status = AvailabilitySlot.NEUTRAL
                    AvailabilitySlot.objects.update_or_create(
                        participant=user,
                        weekday=weekday,
                        half_hour_index=slot_index,
                        defaults={"status": status},
                    )

        ParticipationRecord.objects.filter(external_meeting_id__startswith="demo-").delete()
        now = timezone.now()
        for user, local_timezone in zip(users, timezones):
            for index in range(6):
                ParticipationRecord.objects.create(
                    participant=user,
                    external_meeting_id=f"demo-history-{index}",
                    meeting_title="글로벌 팀 정기 회의",
                    meeting_time_utc=now - timedelta(days=index * 7, hours=index % 3 * 4),
                    local_timezone=local_timezone,
                    local_region=local_timezone,
                    speaking_duration_seconds=240 + index * 30,
                )

        ended_specs = [
            ("demo-summary-q3", "Q3 예산안 협상 (Acme Corp)"),
            ("demo-summary-standup", "주간 팀 스탠드업"),
            ("demo-summary-berlin", "베를린 지사 동기화"),
        ]
        for index, (room_code, title) in enumerate(ended_specs):
            ended, _ = MeetingSession.objects.update_or_create(
                room_code=room_code,
                defaults={"title": title, "host": host, "status": "ENDED", "ended_at": now},
            )
            for user in users:
                MeetingParticipant.objects.update_or_create(
                    meeting=ended,
                    user=user,
                    defaults={"is_host": user == host, "is_active": False, "is_camera_on": False},
                )
            MeetingSummary.objects.update_or_create(
                meeting=ended,
                defaults={"content": "주요 안건과 예산 범위를 검토했으며, 다음 회의 전까지 발표자료와 계약 조건을 보완하기로 했습니다."},
            )
            MeetingMemo.objects.update_or_create(
                meeting=ended,
                user=host,
                content="상대 팀의 우선순위와 다음 협상 포인트를 확인함.",
            )
            ActionItem.objects.update_or_create(
                meeting=ended,
                task="발표자료 수정",
                defaults={"assignee": "지민", "due_date": (now + timedelta(days=7 + index)).date(), "is_completed": False},
            )
            ActionItem.objects.update_or_create(
                meeting=ended,
                task="계약서 검토",
                defaults={"assignee": "Anna", "due_date": None, "is_completed": index == 1},
            )

        self.stdout.write(self.style.SUCCESS("Demo data 준비 완료"))
        self.stdout.write(f"회의: /meeting/{meeting.room_code}")
        if host_created:
            self.stdout.write(f"Host: {host.username} / password: {DEMO_PASSWORD}")
        else:
            self.stdout.write(f"Host: {host.username} / 기존 비밀번호 유지")
        self.stdout.write(f"Demo users: 지민, Anna, Yuki / password: {DEMO_PASSWORD}")
