from rest_framework import serializers

from .models import Card


class CardSerializer(serializers.ModelSerializer):
    """
    조회(list/detail) 응답과 생성(rehearsal→cards 저장) 요청을 겸한다.
    외부 계약 필드명(suggested_text/translated_text/translated_language)은
    rehearsal이 이미 구현해 호출 중인 스펙과 동일하게 맞추고, 모델 내부 컬럼명은
    (text_ko/text_translated/language_code)로 사람이 읽기 쉬운 이름을 쓴다.
    """

    card_id = serializers.UUIDField(source="id", read_only=True)
    suggested_text = serializers.CharField(source="text_ko")
    translated_text = serializers.CharField(source="text_translated")
    translated_language = serializers.CharField(source="language_code")

    class Meta:
        model = Card
        fields = [
            "card_id",
            "partner_tag",
            "situation_label",
            "suggested_text",
            "translated_text",
            "translated_language",
            "explanation",
            "created_at",
        ]
        read_only_fields = ["card_id", "created_at"]

    def create(self, validated_data):
        validated_data["owner"] = self.context["request"].user
        return super().create(validated_data)
