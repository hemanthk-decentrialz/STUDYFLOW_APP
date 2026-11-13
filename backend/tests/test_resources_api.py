"""CRUD contracts, relational rules, soft deletion and SQL-side pagination."""

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "kind,extra,patch",
    [
        (
            "notes",
            {"title": "SQL notes", "content": "Learning joins"},
            {"content": "Revised joins", "expectedVersion": 1},
        ),
        (
            "goals",
            {"title": "Learn SQL", "deadline": "2027-01-01", "progress": 0},
            {"progress": 40},
        ),
        (
            "study-sessions",
            {
                "time": "10:00",
                "scheduledDate": "2027-01-01",
                "durationMinutes": 30,
                "priority": "High",
                "completed": False,
            },
            {"completed": True},
        ),
    ],
)
async def test_resource_lifecycle(actor, kind, extra, patch):
    await actor.course()
    body = {"id": 10, "courseId": 1, **extra}
    created = await actor.request("POST", "/" + kind, body, status=201)
    assert created["courseId"] == 1
    await actor.request("POST", "/" + kind, {**body, "id": 11}, status=409)
    if kind != "study-sessions":
        assert (await actor.request("GET", f"/{kind}/10"))["id"] == 10
    updated = await actor.request("PATCH", f"/{kind}/10", patch)
    for key, value in patch.items():
        if key != "expectedVersion":
            assert updated[key] == value
    await actor.request("DELETE", f"/{kind}/10", status=204)
    assert (await actor.request("GET", "/" + kind))["total"] == 0
    trash = await actor.request("GET", "/deleted-resources")
    assert trash["total"] == 1
    restored = await actor.request("POST", f"/{kind}/10/restore")
    assert restored["id"] == 10
    assert (await actor.request("POST", f"/{kind}/10/restore"))["id"] == 10
    await actor.request("DELETE", "/courses/1", status=409)


async def test_course_crud_and_rename_updates_note_version(actor):
    await actor.course()
    await actor.request(
        "POST", "/notes", {"id": 2, "courseId": 1, "title": "Notes", "content": "Draft"}, status=201
    )
    await actor.request("PATCH", "/courses/1", {"title": "PostgreSQL 18"})
    note = await actor.request("GET", "/notes/2")
    assert note["subject"] == "PostgreSQL 18" and note["version"] == 2
    await actor.request(
        "PATCH", "/notes/2", {"expectedVersion": 1, "content": "Lost edit"}, status=409
    )
    assert (await actor.request("GET", "/notes/2"))["content"] == "Draft"
    await actor.request("DELETE", "/notes/2", status=204)
    await actor.request("DELETE", "/courses/1", status=204)
    await actor.request("POST", "/notes/2/restore", status=404)
    await actor.request("POST", "/courses/1/restore")
    assert (await actor.request("POST", "/notes/2/restore"))["version"] == 4


async def test_goal_course_validation_and_unlink(actor):
    await actor.course()
    await actor.course(2, "Python")
    await actor.request(
        "POST",
        "/goals",
        {"id": 10, "courseId": 1, "title": "SQL", "deadline": "2027-01-01", "progress": 0},
        status=201,
    )
    body = {
        "id": 20,
        "courseId": 2,
        "goalId": 10,
        "time": "09:00",
        "scheduledDate": "2027-01-01",
        "durationMinutes": 30,
        "priority": "Medium",
        "completed": False,
    }
    await actor.request("POST", "/study-sessions", body, status=422)
    await actor.request("POST", "/study-sessions", {**body, "courseId": 1}, status=201)
    await actor.request("DELETE", "/goals/10", status=204)
    assert (await actor.request("GET", "/study-sessions"))["items"][0]["goalId"] is None


async def test_restore_duplicate_conflict(actor):
    await actor.course()
    body = {"id": 2, "courseId": 1, "title": "Same", "content": "Draft"}
    await actor.request("POST", "/notes", body, status=201)
    await actor.request("DELETE", "/notes/2", status=204)
    await actor.request("POST", "/notes", {**body, "id": 3}, status=201)
    await actor.request("POST", "/notes/2/restore", status=409)


async def test_search_filters_sort_and_pagination(actor):
    await actor.course()
    for number in range(12):
        await actor.request(
            "POST",
            "/notes",
            {
                "id": number + 10,
                "courseId": 1,
                "title": f"Note {number:02}",
                "content": "100% ready" if number == 0 else "ordinary",
            },
            status=201,
        )
    first = await actor.request("GET", "/notes", params={"sort_by": "title", "order": "desc"})
    second = await actor.request(
        "GET", "/notes", params={"sort_by": "title", "order": "desc", "page": 2}
    )
    assert first["limit"] == 10 and first["total"] == 12 and first["total_pages"] == 2
    assert len(second["items"]) == 2
    assert {row["id"] for row in first["items"]}.isdisjoint(row["id"] for row in second["items"])
    assert first["items"][0]["title"] == "Note 11"
    assert (await actor.request("GET", "/notes", params={"search": "%", "course_id": 1}))[
        "total"
    ] == 1
    assert (await actor.request("GET", "/notes", params={"search": "' OR 1=1 --"}))["total"] == 0
    assert (await actor.request("GET", "/notes", params={"title": "note 00", "course_id": 1}))[
        "total"
    ] == 1


@pytest.mark.parametrize(
    "query",
    [
        {"limit": 0},
        {"limit": 101},
        {"page": 0},
        {"page": 1001, "limit": 100},
        {"sort_by": "invalid"},
        {"unknown": "value"},
    ],
)
async def test_list_rejects_unbounded_or_unknown_queries(actor, query):
    await actor.request("GET", "/notes", params=query, status=422)


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"id": 0, "courseId": 1, "title": "A", "content": "B"},
        {"id": 1, "courseId": 1, "title": " ", "content": "B"},
        {"id": 1, "courseId": 1, "title": "A", "content": "x" * 100001},
    ],
)
async def test_invalid_notes(actor, body):
    await actor.request("POST", "/notes", body, status=422)


@pytest.mark.parametrize(
    "kind,extra",
    [
        ("notes", {"title": "Private", "content": "Private"}),
        ("goals", {"title": "Private", "deadline": "2027-01-01", "progress": 0}),
        (
            "study-sessions",
            {
                "time": "10:00",
                "scheduledDate": "2027-01-01",
                "durationMinutes": 30,
                "priority": "Low",
                "completed": False,
            },
        ),
    ],
)
async def test_resource_ownership(actor, another_actor, kind, extra):
    await actor.course()
    await actor.request("POST", "/" + kind, {"id": 2, "courseId": 1, **extra}, status=201)
    other = await another_actor()
    await other.request("DELETE", f"/{kind}/2", status=404)
    await other.request("POST", f"/{kind}/2/restore", status=404)
    assert (await other.request("GET", "/" + kind))["total"] == 0
    assert (await actor.request("GET", "/" + kind))["total"] == 1
