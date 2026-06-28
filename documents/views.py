from rest_framework.views import APIView
from rest_framework.response import Response
from documents.services.rag import rag_query


class QueryView(APIView):
    """
    POST a question; get a grounded answer from YOUR tenant's data only.
    Auth required — tenant_id is read from the JWT, never from the request body.
    """

    def post(self, request):
        # Read tenant_id straight from the authenticated user's token.
        # The user cannot override this — it's baked into their JWT.
        tenant_id = request.user.userprofile.tenant_id

        query = request.data.get("query", "").strip()
        if not query:
            return Response({"error": "query is required"}, status=400)

        result = rag_query(query, tenant_id=tenant_id)
        return Response(result)