"""Who may send replies to Zomato for which outlet (the ReplyService table). No active row means no access."""
from .models import ReplyService


def rules_for_client(client_id: int | None) -> list[ReplyService]:
    if not client_id:
        return []
    return list(ReplyService.objects.filter(client_id=client_id, platform="zomato", is_active=True))


def mode_for(rules: list[ReplyService], res_id: str | None) -> str | None:
    """The mode an outlet has ('manual' / 'ai'), or None when it has no access. An outlet's own row beats the client-wide one."""
    own = next((r for r in rules if res_id and r.res_id == str(res_id)), None)
    row = own or next((r for r in rules if not r.res_id), None)
    return row.mode if row else None
