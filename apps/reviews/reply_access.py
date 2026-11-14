"""Who may send replies to Zomato for which outlet: the ReplyService table, keyed by Zomato res ID. No active row means no access."""
from .models import ReplyService


def modes_for(res_ids) -> dict[str, str]:
    """{res_id: 'manual' | 'ai'} for the given Zomato res IDs that have an active row. Anything missing has no access."""
    ids = [str(r) for r in res_ids if r]
    if not ids:
        return {}
    return dict(ReplyService.objects.filter(platform="zomato", is_active=True, res_id__in=ids).values_list("res_id", "mode"))


def mode_for(res_id) -> str | None:
    return modes_for([res_id]).get(str(res_id)) if res_id else None
