from cognitive_sandbox.application.cognitive_runtime import CognitiveRuntime
from cognitive_sandbox.application.memory_retriever import MemoryRetriever
from cognitive_sandbox.domain.cognition import LongTermMemory
from cognitive_sandbox.infrastructure.sqlite_store import SQLiteEventStore


def _memory(memory_id, agent_id, text, *, salience=0.8, created_at="2026-10-11T12:00:00+00:00"):
    return LongTermMemory(
        memory_id=memory_id,
        agent_id=agent_id,
        memory_type="episodic",
        content={"text": text, "channel": "visual"},
        source_refs=(f"observation-{memory_id}",),
        salience=salience,
        created_at=created_at,
    )


def test_retriever_ranks_memories_by_keyword_overlap(tmp_path):
    store = SQLiteEventStore(tmp_path / "retrieval.sqlite3")
    cup = _memory("memory-cup", "lin-xia", "看到玻璃杯碎裂，碎片散落。", salience=0.7)
    room = _memory("memory-room", "lin-xia", "厨房里很安静。", salience=0.99)
    store.append_long_term_memory(cup)
    store.append_long_term_memory(room)

    results = MemoryRetriever(store).retrieve("lin-xia", {"focus": "玻璃杯 碎裂"})

    assert results == [cup]


def test_retriever_returns_only_memories_for_requested_agent(tmp_path):
    store = SQLiteEventStore(tmp_path / "retrieval.sqlite3")
    own = _memory("memory-own", "lin-xia", "A glass cup broke.")
    other = _memory("memory-other", "liang-jing", "A glass cup broke.")
    store.append_long_term_memory(own)
    store.append_long_term_memory(other)

    assert MemoryRetriever(store).retrieve("lin-xia", {"keywords": ["cup", "broke"]}) == [own]
    assert MemoryRetriever(store).retrieve("missing-agent", {"keywords": ["cup"]}) == []


def test_retriever_does_not_return_unrelated_or_empty_query_results(tmp_path):
    store = SQLiteEventStore(tmp_path / "retrieval.sqlite3")
    memory = _memory("memory-cup", "lin-xia", "A glass cup broke.")
    store.append_long_term_memory(memory)
    retriever = MemoryRetriever(store)

    assert retriever.retrieve("lin-xia", {"focus": "garden"}) == []
    assert retriever.retrieve("lin-xia", {}) == []


def test_retrieved_memory_is_activated_through_cognitive_runtime(tmp_path):
    store = SQLiteEventStore(tmp_path / "retrieval.sqlite3")
    memory = _memory("memory-cup", "lin-xia", "A glass cup broke.")
    store.append_long_term_memory(memory)
    retriever = MemoryRetriever(store)
    [retrieved] = retriever.retrieve("lin-xia", {"text": "glass cup"})
    runtime = CognitiveRuntime(
        store,
        id_factory=iter(("proposal-activate", "working-memory-activation")).__next__,
        clock=lambda: "2026-10-11T12:01:00+00:00",
    )

    state = runtime.activate_memory(retrieved)
    [persisted] = store.list_long_term_memories("lin-xia")
    [history] = store.list_cognitive_change_history("lin-xia")

    assert state.cognitive_revision == 1
    assert len(state.working_memory) == 1
    item = state.working_memory[0]
    assert item.content == {
        "memory_id": memory.memory_id,
        "memory_type": "episodic",
        "text": "A glass cup broke.",
        "activated": True,
    }
    assert item.source_refs == memory.source_refs
    assert history["operation"].value == "activate"
    assert history["source_refs"] == memory.source_refs
    assert persisted == memory
