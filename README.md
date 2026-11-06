# discord-admin-mcp

Servidor [MCP](https://modelcontextprotocol.io) em Python para administrar servidores Discord a partir do Claude Code (ou qualquer cliente MCP). Usa a API REST v10 do Discord através do seu próprio bot.

## Ferramentas

| Área | Ferramentas |
|---|---|
| Leitura | `whoami`, `get_guild`, `list_channels`, `list_roles`, `list_members`, `search_members`, `read_messages`, `audit_log`, `list_bans`, `list_invites` |
| Canais | `create_channel`, `edit_channel`, `delete_channel`, `set_channel_permission` |
| Cargos | `create_role`, `edit_role`, `delete_role`, `add_role`, `remove_role` |
| Membros | `set_nickname`, `timeout_member`, `kick_member`, `ban_member`, `unban_member` |
| Mensagens e convites | `send_message`, `delete_message`, `create_invite`, `delete_invite` |

As ações aceitam `reason`, que é registrado no audit log do servidor. Ferramentas destrutivas indicam na descrição que o assistente deve confirmar com você antes de executar.

## Requisitos

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

## 1. Criar o bot

1. Acesse o [Discord Developer Portal](https://discord.com/developers/applications) e clique em **New Application**.
2. Na aba **Bot**:
   - ative **Server Members Intent**;
   - clique em **Reset Token** e copie o token (formato `xxxx.yyyy.zzzz`, ~70 caracteres — não confunda com o *Client Secret* da aba OAuth2).
3. (Opcional, recomendado) Para que só você possa instalar o bot: em **Installation**, defina **Install Link** como *None*; depois, em **Bot**, desmarque **Public Bot**.

## 2. Configurar o token

Nunca coloque o token no código nem faça commit dele.

Windows:

```bash
setx DISCORD_BOT_TOKEN "seu-token"
```

Linux/macOS:

```bash
export DISCORD_BOT_TOKEN="seu-token"
```

Ou copie `.env.example` para `.env` e carregue-o no seu shell (o `.env` está no `.gitignore`).

## 3. Instalar

```bash
git clone <url-deste-repositorio>
cd discord-cli
uv sync
```

Teste a conexão:

```bash
uv run python -c "import discord_admin_mcp as d; print(d.whoami())"
```

## 4. Convidar o bot para o servidor

Troque `SEU_CLIENT_ID` pelo *Application ID* do seu app:

```
https://discord.com/oauth2/authorize?client_id=SEU_CLIENT_ID&scope=bot&permissions=1099914357943
```

Esse valor concede apenas permissões de gestão (sem Administrador): ver audit log, gerenciar servidor, cargos, canais, apelidos e mensagens, expulsar, banir, moderar (castigo), criar convites, ver canais, enviar mensagens e ler histórico.

Depois de autorizar, em **Configurações do servidor → Cargos**, arraste o cargo do bot para **acima** dos cargos que ele deve gerenciar — o Discord só permite que o bot altere cargos e membros abaixo dele.

## 5. Registrar no Claude Code

```bash
claude mcp add discord-admin --scope user -- uv --directory /caminho/para/discord-cli run discord-admin-mcp
```

Abra uma nova sessão e peça, por exemplo: *"liste os membros sem cargo"* ou *"crie o canal #avisos na categoria Comercial"*.

### Outros clientes MCP

```json
{
  "mcpServers": {
    "discord-admin": {
      "command": "uv",
      "args": ["--directory", "/caminho/para/discord-cli", "run", "discord-admin-mcp"],
      "env": { "DISCORD_BOT_TOKEN": "seu-token" }
    }
  }
}
```

## Segurança

- O token só é lido da variável de ambiente `DISCORD_BOT_TOKEN`.
- Quem tem o token controla o bot com todas as permissões dele. Se vazar, use **Reset Token** no portal imediatamente.
- Conceda ao bot só as permissões necessárias e posicione o cargo dele com cuidado.

## Contribuindo

Issues e pull requests são bem-vindos.

## Licença

[MIT](LICENSE)
