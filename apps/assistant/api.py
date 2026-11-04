import time
import uuid
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.outlets import access
from apps.outlets.models import Brand

from .models import AssistantLog


def _who(user):
    if access.is_staff(user):
        return None, "A Codeonto staff member. They may see every client's data."
    m = access.membership(user)
    if m.is_outlet_limited:
        return m.client_id, f"A manager at the client '{m.client.name}'. They may see only the outlets assigned to them."
    return m.client_id, f"A user of the client '{m.client.name}'. They may see only that client's data."


@api_view(["POST"])
def chat(request):
    """{message, thread_id?, context?: {brand_id, outlet_id, start, end, page}} -> {answer, thread_id, queries}"""
    message = (request.data.get("message") or "").strip()
    if not message:
        return Response({"detail": "Write a question first"}, status=400)
    if len(message) > 2000:
        return Response({"detail": "Please keep the question under 2000 characters"}, status=400)
    if not settings.ANTHROPIC_API_KEY or not settings.ASSISTANT_DATABASE_URL or not settings.ASSISTANT_SCOPE_SECRET:
        return Response({"detail": "The assistant is not set up yet: add ANTHROPIC_API_KEY and run `manage.py setup_assistant_role`."}, status=503)
    recent = AssistantLog.objects.filter(user=request.user, created_at__gte=timezone.now() - timedelta(hours=1)).count()
    if recent >= settings.ASSISTANT_MESSAGES_PER_HOUR:
        return Response({"detail": "You have reached the hourly limit for assistant questions. Try again later."}, status=429)

    client_id, who = _who(request.user)
    outlet_ids = access.outlet_limit(request.user)
    ctx = request.data.get("context") or {}
    page = ""
    brand = access.brands_for(request.user).filter(pk=ctx.get("brand_id")).first() if str(ctx.get("brand_id") or "").isdigit() else None
    if brand:
        page = (f"THE USER IS LOOKING AT: brand '{brand.name}' (id {brand.id})"
                + (f", outlet id {ctx['outlet_id']}" if str(ctx.get("outlet_id") or "").isdigit() else ", all outlets")
                + (f", dates {ctx.get('start')} to {ctx.get('end')}" if ctx.get("start") and ctx.get("end") else "")
                + (f", on the '{ctx['page']}' page" if ctx.get("page") else "")
                + ". Questions like 'this month' or 'my outlets' refer to this view unless they say otherwise.")
    thread_id = str(request.data.get("thread_id") or uuid.uuid4())
    started = time.time()
    log = AssistantLog(user=request.user, client_id=client_id, question=message)
    try:
        from .graph import ask
        # the outlets are part of the key so a thread can't recall answers from outlets the manager has since lost
        scope = "" if outlet_ids is None else ",".join(map(str, sorted(outlet_ids)))
        answer, trace = ask(message, f"{request.user.id}:{scope}:{thread_id}", client_id, who, page, outlet_ids=outlet_ids)
        log.answer, log.queries = answer, [{k: v for k, v in q.items() if k != "rows"} for q in trace]
    except Exception as e:
        log.error = f"{type(e).__name__}: {e}"[:1000]
        log.duration_ms = int((time.time() - started) * 1000)
        log.save()
        return Response({"detail": "The assistant hit a problem answering that. Please try again."}, status=502)
    log.duration_ms = int((time.time() - started) * 1000)
    log.save()
    return Response({"answer": answer, "thread_id": thread_id, "queries": trace})
