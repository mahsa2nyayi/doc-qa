from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from . import services
from .serializers import AnswerSerializer, AskSerializer


class AskView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ask"

    @extend_schema(request=AskSerializer, responses=AnswerSerializer)
    def post(self, request):
        """Ask a question about your documents. Every answer comes with the
        passages it was based on, including document and page."""
        params = AskSerializer(data=request.data)
        params.is_valid(raise_exception=True)
        data = params.validated_data

        result = services.answer_question(
            user=request.user,
            question=data["question"],
            top_k=data["top_k"],
            document_ids=data.get("document_ids"),
        )
        payload = {
            "question": data["question"],
            "answer": result.text,
            "mode": result.mode,
            "sources": [
                {
                    "document_id": hit.chunk.document_id,
                    "document_title": hit.chunk.document.title,
                    "page": hit.chunk.page,
                    "score": round(hit.score, 4),
                    "text": hit.chunk.text,
                }
                for hit in result.hits
            ],
        }
        return Response(AnswerSerializer(payload).data)
