from __future__ import annotations

from workers import tasks


def test_worker_phase_tasks_are_split(monkeypatch) -> None:
    calls: list[str] = []
    brand = {"id": "brand-1", "name": "PW"}

    monkeypatch.setattr(tasks, "_get_target_brands", lambda brand_id=None: [brand])
    monkeypatch.setattr(tasks, "_submit_youtube_title_triage_batch", lambda b, **kwargs: calls.append("submit") or {"phase": "submit"})
    monkeypatch.setattr(tasks, "_poll_youtube_title_triage_batch", lambda b, **kwargs: calls.append("poll") or {"phase": "poll"})
    monkeypatch.setattr(
        tasks,
        "_ingest_youtube_title_triage_results",
        lambda **kwargs: calls.append("ingest") or {"phase": "ingest", "batch": kwargs.get("batch_meta")},
    )
    monkeypatch.setattr(tasks, "_enrich_flagged_youtube_mentions", lambda b, video_ids: calls.append("enrich") or {"phase": "enrich", "video_ids": video_ids})

    submit_out = tasks.submit_youtube_title_triage_batch.run(brand_id="brand-1")
    poll_out = tasks.poll_youtube_title_triage_batch.run(brand_id="brand-1")
    ingest_out = tasks.ingest_youtube_title_triage_results.run(
        brand_id="brand-1",
        batch_meta={"provider_batch_id": "batch-1"},
        target_custom_ids=["cid-1"],
    )
    enrich_out = tasks.enrich_flagged_youtube_mentions.run(
        brand_id="brand-1",
        flagged_video_ids=["vid-1"],
    )

    assert submit_out and submit_out[0]["phase"] == "submit"
    assert poll_out and poll_out[0]["phase"] == "poll"
    assert ingest_out["phase"] == "ingest"
    assert enrich_out["phase"] == "enrich"
    assert calls == ["submit", "poll", "ingest", "enrich"]


def test_scrape_platform_youtube_runs_sync_ingestion_only(monkeypatch) -> None:
    calls: list[str] = []
    brand = {"id": "brand-1", "name": "PW"}

    monkeypatch.setattr(tasks, "get_monitored_brands", lambda: [brand])
    monkeypatch.setattr(
        tasks,
        "_run_youtube_title_triage_sync_ingestion",
        lambda b, **kwargs: calls.append("sync") or {
            "discovered": 1,
            "titles_triaged": 1,
            "triage_chunks_processed": 1,
            "enrichment_triggered": False,
        },
    )

    tasks.scrape_platform.run("youtube")

    assert calls == ["sync"]


def test_sync_ingestion_task_calls_sync_helper(monkeypatch) -> None:
    brand = {"id": "brand-1", "name": "PW"}
    calls: list[int] = []

    monkeypatch.setattr(tasks, "_get_target_brands", lambda brand_id=None: [brand])
    monkeypatch.setattr(
        tasks,
        "_run_youtube_title_triage_sync_ingestion",
        lambda b, **kwargs: calls.append(int(kwargs.get("triage_batch_size", 0))) or {"phase": "sync"},
    )

    out = tasks.run_youtube_title_triage_sync_ingestion.run(
        brand_id="brand-1",
        triage_batch_size=10,
    )

    assert out and out[0]["phase"] == "sync"
    assert calls == [10]


def test_layer2_sync_task_calls_layer2_helper(monkeypatch) -> None:
    brand = {"id": "brand-1", "name": "PW"}
    calls: list[tuple[int, int, bool, bool]] = []

    monkeypatch.setattr(tasks, "_get_target_brands", lambda brand_id=None: [brand])
    monkeypatch.setattr(
        tasks,
        "_run_youtube_layer2_sync_fetch",
        lambda b, **kwargs: calls.append(
            (
                int(kwargs.get("page_size", 0)),
                int(kwargs.get("page_offset", 0)),
                bool(kwargs.get("include_completed")),
                bool(kwargs.get("use_fallback_transcript")),
            )
        )
        or {"phase": "layer2"},
    )

    out = tasks.run_youtube_layer2_sync_fetch.run(
        brand_id="brand-1",
        page_size=25,
        page_offset=50,
        include_completed=True,
        use_fallback_transcript=False,
    )

    assert out and out[0]["phase"] == "layer2"
    assert calls == [(25, 50, True, False)]


def test_transcript_sentiment_task_calls_helper(monkeypatch) -> None:
    brand = {"id": "brand-1", "name": "PW"}
    calls: list[tuple[int, int, bool]] = []

    monkeypatch.setattr(tasks, "_get_target_brands", lambda brand_id=None: [brand])
    monkeypatch.setattr(
        tasks,
        "_run_youtube_transcript_sentiment_sync",
        lambda b, **kwargs: calls.append(
            (
                int(kwargs.get("page_size", 0)),
                int(kwargs.get("page_offset", 0)),
                bool(kwargs.get("force_reprocess")),
            )
        )
        or {"phase": "transcript_sentiment"},
    )

    out = tasks.run_youtube_transcript_sentiment_sync.run(
        brand_id="brand-1",
        page_size=10,
        page_offset=5,
        force_reprocess=True,
    )

    assert out and out[0]["phase"] == "transcript_sentiment"
    assert calls == [(10, 5, True)]


def test_comment_sentiment_task_calls_helper(monkeypatch) -> None:
    brand = {"id": "brand-1", "name": "PW"}
    calls: list[tuple[int, int]] = []

    monkeypatch.setattr(tasks, "_get_target_brands", lambda brand_id=None: [brand])
    monkeypatch.setattr(
        tasks,
        "_run_youtube_comment_sentiment_sync",
        lambda b, **kwargs: calls.append(
            (
                int(kwargs.get("video_page_size", 0)),
                int(kwargs.get("comment_batch_size", 0)),
            )
        )
        or {"phase": "comment_sentiment"},
    )

    out = tasks.run_youtube_comment_sentiment_sync.run(
        brand_id="brand-1",
        video_page_size=25,
        comment_batch_size=20,
    )

    assert out and out[0]["phase"] == "comment_sentiment"
    assert calls == [(25, 20)]
