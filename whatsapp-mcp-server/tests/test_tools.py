import asyncio
import importlib
import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SELF = "5511999990000@s.whatsapp.net"
OTHER = "5511888880000@s.whatsapp.net"
LID = "77001@lid"


@pytest.fixture()
def server(tmp_path, monkeypatch):
    db = tmp_path / "messages.db"
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE chats (jid TEXT PRIMARY KEY, name TEXT, last_message_time TIMESTAMP);
        CREATE TABLE messages (id TEXT, chat_jid TEXT, sender TEXT, content TEXT, timestamp TIMESTAMP,
            is_from_me BOOLEAN, media_type TEXT, filename TEXT, url TEXT, media_key BLOB,
            file_sha256 BLOB, file_enc_sha256 BLOB, file_length INTEGER, PRIMARY KEY (id, chat_jid));
        """
    )
    conn.executemany(
        "INSERT INTO chats VALUES (?, ?, ?)",
        [(SELF, "Eu", "2026-11-10 10:00:02"), (OTHER, "Fulano", "2026-11-10 09:00:00")],
    )
    conn.executemany(
        "INSERT INTO messages (id, chat_jid, sender, content, timestamp, is_from_me, media_type) VALUES (?,?,?,?,?,?,?)",
        [
            ("A", SELF, "5511999990000", "aviso", "2026-11-10 10:00:00", 1, None),
            ("B", SELF, "5511999990000", "resposta", "2026-11-10 10:00:02", 1, None),
            ("C", OTHER, "5511888880000", "oi", "2026-11-10 09:00:00", 0, None),
        ],
    )
    conn.execute("INSERT INTO chats VALUES (?, ?, ?)", (LID, None, "2026-11-10 11:00:00"))
    conn.execute(
        "INSERT INTO messages (id, chat_jid, sender, content, timestamp, is_from_me) VALUES (?,?,?,?,?,?)",
        ("D", LID, "77001", "ok pode seguir", "2026-11-10 11:00:00", 0),
    )
    conn.commit()
    conn.close()
    meow = sqlite3.connect(tmp_path / "whatsapp.db")
    meow.execute("CREATE TABLE whatsmeow_lid_map (lid TEXT PRIMARY KEY, pn TEXT UNIQUE NOT NULL)")
    meow.execute("INSERT INTO whatsmeow_lid_map VALUES ('77001', '5511777770000')")
    meow.commit()
    meow.close()
    monkeypatch.setenv("MESSAGES_DB_PATH", str(db))
    monkeypatch.delenv("WHATSMEOW_DB_PATH", raising=False)
    for name in ("whatsapp", "main"):
        sys.modules.pop(name, None)
    return importlib.import_module("main")


def call(server, tool, args):
    result = asyncio.run(server.mcp.call_tool(tool, args))
    structured = result[1] if isinstance(result, tuple) else result
    return structured.get("result", structured) if isinstance(structured, dict) else structured


def test_list_messages_returns_structured_messages(server):
    msgs = call(server, "list_messages", {"include_context": False, "limit": 10})
    assert [m["id"] for m in msgs] == ["D", "B", "A", "C"]
    assert msgs[1]["is_from_me"] is True
    assert msgs[3]["sender_name"] == "Fulano"


def test_list_messages_empty_is_empty_list(server):
    assert call(server, "list_messages", {"query": "inexistente", "include_context": False}) == []


def test_list_messages_since_is_oldest_first_and_inclusive(server):
    msgs = call(server, "list_messages_since", {"after": "2026-11-10T10:00:00", "chat_jid": SELF})
    assert [m["id"] for m in msgs] == ["A", "B"]


def test_list_messages_since_by_phone_resolves_lid(server):
    msgs = call(server, "list_messages_since", {"after": "2026-11-10T00:00:00", "phone": "+55 11 77777-0000"})
    assert [(m["id"], m["chat_jid"], m["is_from_me"]) for m in msgs] == [("D", LID, False)]


def test_list_messages_since_by_phone_without_lid_uses_phone_jid(server):
    msgs = call(server, "list_messages_since", {"after": "2026-11-10T00:00:00", "phone": "5511888880000"})
    assert [m["id"] for m in msgs] == ["C"]


def test_list_messages_since_rejects_bad_date(server):
    with pytest.raises(Exception):
        call(server, "list_messages_since", {"after": "ontem"})


def test_direct_chat_missing_returns_none(server):
    assert call(server, "get_direct_chat_by_contact", {"sender_phone_number": "424242"}) is None


def test_list_chats_and_contacts_are_dicts(server):
    chats = call(server, "list_chats", {"limit": 5})
    assert [c["jid"] for c in chats] == [LID, SELF, OTHER]
    assert chats[1]["is_group"] is False
    contacts = call(server, "search_contacts", {"query": "Fulano"})
    assert contacts == [{"phone_number": "5511888880000", "name": "Fulano", "jid": OTHER}]


def test_message_context_is_dict(server):
    ctx = call(server, "get_message_context", {"message_id": "A", "before": 1, "after": 1})
    assert ctx["message"]["id"] == "A" and [m["id"] for m in ctx["after"]] == ["B"]
    json.dumps(ctx)
