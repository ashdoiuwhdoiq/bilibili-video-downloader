# Download Progress Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add real-time backend download progress, speed, and status updates to the frontend for Bilibili downloads.

**Architecture:** Introduce in-memory download tasks on the Flask side, stream task events over SSE, and let the React client create a task, subscribe to updates, then fetch the finished file. Keep yt-dlp progress handling in backend helpers so both task state and tests stay focused.

**Tech Stack:** Flask, yt-dlp progress hooks, Python threading, Server-Sent Events, React, Vitest, unittest

---

## Chunk 1: Backend Task Lifecycle

### Task 1: Add failing backend tests

**Files:**
- Modify: `E:\BISU\整活\代码创作\bilibili-video-downloader\tests\test_api_behavior.py`

- [ ] Add tests for task progress payload updates and completion state.
- [ ] Run `python -m unittest tests.test_api_behavior` and confirm the new tests fail for missing helpers.

### Task 2: Implement in-memory download task helpers

**Files:**
- Modify: `E:\BISU\整活\代码创作\bilibili-video-downloader\api.py`

- [ ] Add task creation, task lookup, and task progress update helpers.
- [ ] Add yt-dlp progress hook integration and completion/error state transitions.
- [ ] Re-run `python -m unittest tests.test_api_behavior`.

## Chunk 2: Backend API Surface

### Task 3: Add task-based download endpoints

**Files:**
- Modify: `E:\BISU\整活\代码创作\bilibili-video-downloader\api.py`

- [ ] Add `POST /api/download-tasks`.
- [ ] Add `GET /api/download-tasks/<task_id>/events`.
- [ ] Add `GET /api/download-tasks/<task_id>/file`.
- [ ] Verify backend tests still pass.

## Chunk 3: Frontend Progress Flow

### Task 4: Add failing frontend tests for progress helpers

**Files:**
- Create: `E:\BISU\整活\代码创作\bilibili-video-downloader\src\lib\download-progress.ts`
- Create: `E:\BISU\整活\代码创作\bilibili-video-downloader\src\lib\download-progress.test.ts`

- [ ] Add tests for formatting bytes, speed, percent, and status messages.
- [ ] Run `npm test -- src/lib/download-progress.test.ts` and confirm failure first.

### Task 5: Implement frontend task flow and progress UI

**Files:**
- Modify: `E:\BISU\整活\代码创作\bilibili-video-downloader\src\App.tsx`
- Modify: `E:\BISU\整活\代码创作\bilibili-video-downloader\src\lib\download-progress.ts`

- [ ] Create task before download.
- [ ] Subscribe to SSE updates and render live progress.
- [ ] Trigger final file download when task finishes.
- [ ] Surface errors and reset state cleanly.

### Task 6: Verify

**Files:**
- No code changes expected

- [ ] Run `python -m unittest tests.test_api_behavior`.
- [ ] Run `npm test`.
- [ ] Run `npm run build`.
