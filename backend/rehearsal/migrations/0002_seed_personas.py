import uuid

from django.db import migrations

PERSONAS = [
    {
        "name": "독일 팀장님",
        "culture_tag": "DE",
        "language_code": "de",
        "description": "직설적이고 사실 기반의 커뮤니케이션을 선호하는 독일 팀장",
        "display_order": 1,
    },
    {
        "name": "일본 클라이언트",
        "culture_tag": "JP",
        "language_code": "ja",
        "description": "완곡하고 예의를 중시하는 커뮤니케이션을 선호하는 일본 클라이언트",
        "display_order": 2,
    },
    {
        "name": "중국 파트너",
        "culture_tag": "CN",
        "language_code": "zh",
        "description": "관계와 협상의 유연성을 중시하는 중국 비즈니스 파트너",
        "display_order": 3,
    },
    {
        "name": "미국 동료",
        "culture_tag": "US",
        "language_code": "en",
        "description": "캐주얼하고 직접적인 커뮤니케이션을 선호하는 미국 동료",
        "display_order": 4,
    },
]


def seed_personas(apps, schema_editor):
    Persona = apps.get_model("rehearsal", "Persona")
    for data in PERSONAS:
        Persona.objects.get_or_create(
            culture_tag=data["culture_tag"],
            defaults={"id": uuid.uuid4(), **data},
        )


def remove_personas(apps, schema_editor):
    Persona = apps.get_model("rehearsal", "Persona")
    Persona.objects.filter(culture_tag__in=[p["culture_tag"] for p in PERSONAS]).delete()


class Migration(migrations.Migration):
    dependencies = [("rehearsal", "0001_initial")]
    operations = [migrations.RunPython(seed_personas, remove_personas)]
