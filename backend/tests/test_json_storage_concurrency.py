"""Regression tests: JSON storage updates must be atomic under concurrent writers.

Historically the JSON backend performed read-modify-write with separate locks for read
(shared) and write (exclusive), which can lose updates when two requests write the same
conversation concurrently.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import threading


def test_json_add_user_message_is_atomic_under_concurrent_writes(tmp_path, monkeypatch):
    from .. import storage

    # Force JSON mode and isolate storage to a temp dir.
    monkeypatch.setattr(storage, "is_using_database", lambda: False)
    monkeypatch.setattr(storage.config, "DATA_DIR", str(tmp_path))

    conversation_id = "00000000-0000-0000-0000-000000001001"
    storage.create_conversation(conversation_id, models=None, chairman=None, username=None)

    barrier = threading.Barrier(2)
    real_get_conversation = storage.get_conversation

    def gated_get_conversation(cid):
        conv = real_get_conversation(cid)
        barrier.wait(timeout=5)
        return conv

    # Force both writers to read the same initial state before either writes.
    monkeypatch.setattr(storage, "get_conversation", gated_get_conversation)

    def worker(msg):
        storage.add_user_message(conversation_id, msg)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker, "m1"), pool.submit(worker, "m2")]
        for f in futures:
            f.result(timeout=10)

    loaded = real_get_conversation(conversation_id)
    contents = [m.get("content") for m in loaded.get("messages", []) if m.get("role") == "user"]

    assert sorted(contents) == ["m1", "m2"], "Both user messages must be preserved"


def test_json_add_assistant_message_is_atomic_under_concurrent_writes(tmp_path, monkeypatch):
    from .. import storage

    monkeypatch.setattr(storage, "is_using_database", lambda: False)
    monkeypatch.setattr(storage.config, "DATA_DIR", str(tmp_path))

    conversation_id = "00000000-0000-0000-0000-000000001002"
    storage.create_conversation(conversation_id, models=None, chairman=None, username=None)

    barrier = threading.Barrier(2)
    real_get_conversation = storage.get_conversation

    def gated_get_conversation(cid):
        conv = real_get_conversation(cid)
        barrier.wait(timeout=5)
        return conv

    monkeypatch.setattr(storage, "get_conversation", gated_get_conversation)

    def worker(resp):
        storage.add_assistant_message(
            conversation_id,
            stage1=[{"model": "m", "response": resp}],
            stage2=None,
            stage3=None,
            metadata={"execution_mode": "chat_only"},
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker, "r1"), pool.submit(worker, "r2")]
        for f in futures:
            f.result(timeout=10)

    loaded = real_get_conversation(conversation_id)
    assistant = [m for m in loaded.get("messages", []) if m.get("role") == "assistant"]
    stage1_responses = [m.get("stage1", [{}])[0].get("response") for m in assistant]

    assert sorted(stage1_responses) == ["r1", "r2"], "Both assistant messages must be preserved"
