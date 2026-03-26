from __future__ import annotations

try:
    from livekit import api
except Exception:  # pragma: no cover
    api = None


def issue_token(api_key: str, api_secret: str, room: str, identity: str) -> str | None:
    if api is None:
        return None
    token = (
        api.AccessToken(api_key, api_secret)
        .with_identity(identity)
        .with_name(identity)
        .with_grants(api.VideoGrants(room_join=True, room=room, can_publish=True, can_subscribe=True))
    )
    return token.to_jwt()

