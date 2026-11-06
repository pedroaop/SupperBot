"""Servidor MCP para administraÃ§Ã£o de servidores Discord (API REST v10).

O token do bot vem da variÃ¡vel de ambiente DISCORD_BOT_TOKEN.
"""

from __future__ import annotations

import os
import sys
from typing import Any

import httpx
from mcp.server.mcpserver import MCPServer

API = "https://discord.com/api/v10"
mcp = MCPServer("discord-admin")


def _token() -> str:
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token and sys.platform == "win32":
        # setx grava no registro; processos jÃ¡ abertos nÃ£o herdam a variÃ¡vel.
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                token = winreg.QueryValueEx(key, "DISCORD_BOT_TOKEN")[0]
        except OSError:
            pass
    if not token:
        raise RuntimeError("Defina a variÃ¡vel de ambiente DISCORD_BOT_TOKEN.")
    return token


_client: httpx.Client | None = None


def _http() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(
            base_url=API,
            headers={"Authorization": f"Bot {_token()}", "User-Agent": "DiscordBot (discord-admin-mcp, 0.1)"},
            timeout=30,
        )
    return _client


def _req(method: str, path: str, *, reason: str | None = None, **kw: Any) -> Any:
    headers = {"X-Audit-Log-Reason": reason} if reason else None
    r = _http().request(method, path, headers=headers, **kw)
    if r.status_code == 429:
        raise RuntimeError(f"Rate limit: tente de novo em {r.json().get('retry_after')}s")
    if r.is_error:
        raise RuntimeError(f"Discord {r.status_code}: {r.text}")
    return r.json() if r.content else {"ok": True}


# ---------- Leitura ----------

@mcp.tool()
def whoami() -> dict:
    """Mostra o usuÃ¡rio do bot e os servidores onde ele estÃ¡."""
    me = _req("GET", "/users/@me")
    guilds = _req("GET", "/users/@me/guilds")
    return {"bot": {"id": me["id"], "username": me["username"]},
            "guilds": [{"id": g["id"], "name": g["name"]} for g in guilds]}


@mcp.tool()
def get_guild(guild_id: str) -> dict:
    """Detalhes de um servidor (nome, dono, contagem aproximada de membros)."""
    g = _req("GET", f"/guilds/{guild_id}", params={"with_counts": "true"})
    keys = ("id", "name", "owner_id", "approximate_member_count", "approximate_presence_count",
            "verification_level", "premium_tier", "description")
    return {k: g.get(k) for k in keys}


@mcp.tool()
def list_channels(guild_id: str) -> list[dict]:
    """Lista canais e categorias. type: 0=texto, 2=voz, 4=categoria, 5=anÃºncios, 15=fÃ³rum."""
    chans = _req("GET", f"/guilds/{guild_id}/channels")
    return sorted(({k: c.get(k) for k in ("id", "name", "type", "parent_id", "position", "topic")}
                   for c in chans), key=lambda c: (c["parent_id"] or "", c["position"]))


@mcp.tool()
def list_roles(guild_id: str) -> list[dict]:
    """Lista cargos com posiÃ§Ã£o e permissÃµes."""
    roles = _req("GET", f"/guilds/{guild_id}/roles")
    return sorted(({k: r.get(k) for k in ("id", "name", "position", "permissions", "color", "hoist", "mentionable", "managed")}
                   for r in roles), key=lambda r: -r["position"])


@mcp.tool()
def list_members(guild_id: str, limit: int = 1000, after: str = "0") -> list[dict]:
    """Lista membros (atÃ© 1000 por chamada; use `after` com o Ãºltimo id para paginar)."""
    ms = _req("GET", f"/guilds/{guild_id}/members", params={"limit": min(limit, 1000), "after": after})
    return [{"id": m["user"]["id"], "username": m["user"]["username"], "nick": m.get("nick"),
             "bot": m["user"].get("bot", False), "roles": m["roles"], "joined_at": m["joined_at"]} for m in ms]


@mcp.tool()
def search_members(guild_id: str, query: str, limit: int = 25) -> list[dict]:
    """Busca membros cujo nome ou apelido comeÃ§a com `query`."""
    ms = _req("GET", f"/guilds/{guild_id}/members/search", params={"query": query, "limit": limit})
    return [{"id": m["user"]["id"], "username": m["user"]["username"], "nick": m.get("nick"), "roles": m["roles"]} for m in ms]


@mcp.tool()
def read_messages(channel_id: str, limit: int = 50) -> list[dict]:
    """LÃª as mensagens mais recentes de um canal (mÃ¡x. 100)."""
    ms = _req("GET", f"/channels/{channel_id}/messages", params={"limit": min(limit, 100)})
    return [{"id": m["id"], "author": m["author"]["username"], "content": m["content"], "timestamp": m["timestamp"]} for m in ms]


@mcp.tool()
def audit_log(guild_id: str, limit: int = 50, user_id: str | None = None, action_type: int | None = None) -> list[dict]:
    """Ãšltimas entradas do registro de auditoria."""
    params: dict[str, Any] = {"limit": min(limit, 100)}
    if user_id:
        params["user_id"] = user_id
    if action_type is not None:
        params["action_type"] = action_type
    data = _req("GET", f"/guilds/{guild_id}/audit-logs", params=params)
    users = {u["id"]: u["username"] for u in data.get("users", [])}
    return [{"id": e["id"], "action_type": e["action_type"], "by": users.get(e.get("user_id"), e.get("user_id")),
             "target_id": e.get("target_id"), "reason": e.get("reason"), "changes": e.get("changes")}
            for e in data.get("audit_log_entries", [])]


@mcp.tool()
def list_bans(guild_id: str) -> list[dict]:
    """Lista usuÃ¡rios banidos."""
    return [{"id": b["user"]["id"], "username": b["user"]["username"], "reason": b.get("reason")}
            for b in _req("GET", f"/guilds/{guild_id}/bans")]


@mcp.tool()
def list_invites(guild_id: str) -> list[dict]:
    """Lista convites ativos."""
    return [{"code": i["code"], "channel": i["channel"]["name"], "uses": i.get("uses"), "max_uses": i.get("max_uses"),
             "inviter": (i.get("inviter") or {}).get("username"), "expires_at": i.get("expires_at")}
            for i in _req("GET", f"/guilds/{guild_id}/invites")]


# ---------- Escrita ----------

@mcp.tool()
def create_channel(guild_id: str, name: str, type: int = 0, parent_id: str | None = None,
                   topic: str | None = None, reason: str | None = None) -> dict:
    """Cria canal. type: 0=texto, 2=voz, 4=categoria, 5=anÃºncios, 15=fÃ³rum."""
    body = {k: v for k, v in {"name": name, "type": type, "parent_id": parent_id, "topic": topic}.items() if v is not None}
    c = _req("POST", f"/guilds/{guild_id}/channels", json=body, reason=reason)
    return {"id": c["id"], "name": c["name"], "type": c["type"]}


@mcp.tool()
def edit_channel(channel_id: str, name: str | None = None, topic: str | None = None,
                 parent_id: str | None = None, position: int | None = None, reason: str | None = None) -> dict:
    """Edita nome, tÃ³pico, categoria ou posiÃ§Ã£o de um canal."""
    body = {k: v for k, v in {"name": name, "topic": topic, "parent_id": parent_id, "position": position}.items() if v is not None}
    c = _req("PATCH", f"/channels/{channel_id}", json=body, reason=reason)
    return {"id": c["id"], "name": c["name"]}


@mcp.tool()
def delete_channel(channel_id: str, reason: str | None = None) -> dict:
    """APAGA um canal permanentemente. Confirme com o usuÃ¡rio antes."""
    c = _req("DELETE", f"/channels/{channel_id}", reason=reason)
    return {"deleted": c["id"], "name": c.get("name")}


@mcp.tool()
def set_channel_permission(channel_id: str, target_id: str, target_type: int, allow: str = "0",
                           deny: str = "0", reason: str | None = None) -> dict:
    """Define override de permissÃ£o no canal. target_type: 0=cargo, 1=membro. allow/deny sÃ£o bitfields."""
    return _req("PUT", f"/channels/{channel_id}/permissions/{target_id}",
                json={"type": target_type, "allow": allow, "deny": deny}, reason=reason)


@mcp.tool()
def create_role(guild_id: str, name: str, permissions: str = "0", color: int = 0,
                hoist: bool = False, mentionable: bool = False, reason: str | None = None) -> dict:
    """Cria um cargo."""
    r = _req("POST", f"/guilds/{guild_id}/roles", reason=reason,
             json={"name": name, "permissions": permissions, "color": color, "hoist": hoist, "mentionable": mentionable})
    return {"id": r["id"], "name": r["name"]}


@mcp.tool()
def edit_role(guild_id: str, role_id: str, name: str | None = None, permissions: str | None = None,
              color: int | None = None, hoist: bool | None = None, mentionable: bool | None = None,
              reason: str | None = None) -> dict:
    """Edita um cargo."""
    body = {k: v for k, v in {"name": name, "permissions": permissions, "color": color,
                               "hoist": hoist, "mentionable": mentionable}.items() if v is not None}
    r = _req("PATCH", f"/guilds/{guild_id}/roles/{role_id}", json=body, reason=reason)
    return {"id": r["id"], "name": r["name"]}


@mcp.tool()
def delete_role(guild_id: str, role_id: str, reason: str | None = None) -> dict:
    """APAGA um cargo. Confirme com o usuÃ¡rio antes."""
    return _req("DELETE", f"/guilds/{guild_id}/roles/{role_id}", reason=reason)


@mcp.tool()
def add_role(guild_id: str, user_id: str, role_id: str, reason: str | None = None) -> dict:
    """Atribui um cargo a um membro."""
    return _req("PUT", f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}", reason=reason)


@mcp.tool()
def remove_role(guild_id: str, user_id: str, role_id: str, reason: str | None = None) -> dict:
    """Remove um cargo de um membro."""
    return _req("DELETE", f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}", reason=reason)


@mcp.tool()
def set_nickname(guild_id: str, user_id: str, nick: str | None, reason: str | None = None) -> dict:
    """Define (ou limpa, com null) o apelido de um membro."""
    m = _req("PATCH", f"/guilds/{guild_id}/members/{user_id}", json={"nick": nick}, reason=reason)
    return {"id": m["user"]["id"], "nick": m.get("nick")}


@mcp.tool()
def timeout_member(guild_id: str, user_id: str, until_iso: str | None, reason: str | None = None) -> dict:
    """Silencia (castigo) um membro atÃ© a data ISO 8601 (mÃ¡x. 28 dias). null remove o castigo."""
    m = _req("PATCH", f"/guilds/{guild_id}/members/{user_id}",
             json={"communication_disabled_until": until_iso}, reason=reason)
    return {"id": m["user"]["id"], "until": m.get("communication_disabled_until")}


@mcp.tool()
def kick_member(guild_id: str, user_id: str, reason: str | None = None) -> dict:
    """EXPULSA um membro. Confirme com o usuÃ¡rio antes."""
    return _req("DELETE", f"/guilds/{guild_id}/members/{user_id}", reason=reason)


@mcp.tool()
def ban_member(guild_id: str, user_id: str, delete_message_seconds: int = 0, reason: str | None = None) -> dict:
    """BANE um membro. Confirme com o usuÃ¡rio antes."""
    return _req("PUT", f"/guilds/{guild_id}/bans/{user_id}",
                json={"delete_message_seconds": delete_message_seconds}, reason=reason)


@mcp.tool()
def unban_member(guild_id: str, user_id: str, reason: str | None = None) -> dict:
    """Remove o banimento de um usuÃ¡rio."""
    return _req("DELETE", f"/guilds/{guild_id}/bans/{user_id}", reason=reason)


@mcp.tool()
def send_message(channel_id: str, content: str) -> dict:
    """Envia mensagem num canal como o bot."""
    m = _req("POST", f"/channels/{channel_id}/messages", json={"content": content})
    return {"id": m["id"], "channel_id": m["channel_id"]}


@mcp.tool()
def delete_message(channel_id: str, message_id: str, reason: str | None = None) -> dict:
    """APAGA uma mensagem. Confirme com o usuÃ¡rio antes."""
    return _req("DELETE", f"/channels/{channel_id}/messages/{message_id}", reason=reason)


@mcp.tool()
def create_invite(channel_id: str, max_age: int = 86400, max_uses: int = 0, temporary: bool = False) -> dict:
    """Cria convite (max_age em segundos, 0 = nunca expira; max_uses 0 = ilimitado)."""
    i = _req("POST", f"/channels/{channel_id}/invites",
             json={"max_age": max_age, "max_uses": max_uses, "temporary": temporary, "unique": True})
    return {"url": f"https://discord.gg/{i['code']}", "expires_in": max_age}


@mcp.tool()
def delete_invite(code: str, reason: str | None = None) -> dict:
    """Revoga um convite."""
    i = _req("DELETE", f"/invites/{code}", reason=reason)
    return {"revoked": i.get("code", code)}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

