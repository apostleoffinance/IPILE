from sqlalchemy import or_

from app.api.deps import HouseholdContext


def account_visibility(query, model, ctx: HouseholdContext):
    """Owners/partners manage the household ledger; other roles see shared and own records only."""
    if ctx.role in {"owner", "partner"}:
        return query
    if ctx.role == "member":
        return query.filter(
            or_(
                model.access_scope == "shared",
                (model.access_scope == "personal") & (model.owner_member_id == ctx.member.id),
            )
        )
    return query.filter(model.access_scope == "shared")


def transaction_visibility(query, model, ctx: HouseholdContext):
    if ctx.role in {"owner", "partner"}:
        return query
    if ctx.role == "member":
        return query.filter(
            or_(
                model.access_scope == "shared",
                (model.access_scope == "personal") & (model.member_id == ctx.member.id),
            )
        )
    return query.filter(model.access_scope == "shared")
