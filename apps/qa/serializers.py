from rest_framework import serializers


class AskSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=1000)
    top_k = serializers.IntegerField(min_value=1, max_value=10, default=5)
    document_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        max_length=50,
        help_text="Restrict the search to these documents (default: all of yours).",
    )


class SourceSerializer(serializers.Serializer):
    document_id = serializers.IntegerField()
    document_title = serializers.CharField()
    page = serializers.IntegerField()
    score = serializers.FloatField()
    text = serializers.CharField()


class AnswerSerializer(serializers.Serializer):
    question = serializers.CharField()
    answer = serializers.CharField(allow_null=True)
    mode = serializers.ChoiceField(choices=["extractive", "llm", "no_results"])
    sources = SourceSerializer(many=True)
