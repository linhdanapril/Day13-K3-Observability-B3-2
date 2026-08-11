# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: B3_2
- Repository URL: https://github.com/linhdanapril/Day13-K3-Observability-B3-2
- Commit SHA cuối: `c84e992`
- Thành viên và vai trò:
  - Bùi Linh Đan (01177) — CP1: Middleware, Correlation ID, JSON Logging
  - Lại Thế Rin (01665) — CP1: PII Scrubbing, Patterns, Metrics
  - Trương Thảo Nguyên (01389) — CP2: Langfuse, Dashboard, Alerts
  - Cao Thị Thu Trang (01885) — CP2: Prompt Versioning, SLO, Validation
  - Bùi Thị Như Ngọc (01882) — CP3: Streamlit Dashboard, Investigation
  - Trần Dương Tuấn (01271) — CP3: Challenge Traces, Fix, Audit

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: 100/100 (baseline 30/100 — [evidence/validate_logs_baseline.txt](evidence/validate_logs_baseline.txt))
- Tổng số traces: 115 (đếm qua Langfuse API, [evidence/traces_list.txt](evidence/traces_list.txt))
- Số PII leak còn lại: 0
- Link/đường dẫn dashboard:
  - Dashboard tĩnh (HTML): [evidence/dashboard.html](evidence/dashboard.html) + [evidence/dashboard.png](evidence/dashboard.png)
  - Dashboard live (Streamlit): [evidence/dashboard-challenge-rag_slow.png](evidence/dashboard-challenge-rag_slow.png)

## 3. Logging và tracing

- Evidence correlation ID: [evidence/cp1_log_evidence.txt](evidence/cp1_log_evidence.txt) — log `request_received` có `correlation_id: req-1ead3d37` + metadata `user_id_hash`, `session_id`, `feature`, `model`, `env`
- Evidence PII redaction: [evidence/cp1_log_evidence.txt](evidence/cp1_log_evidence.txt) — `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, `[REDACTED_CREDIT_CARD]` không xuất hiện nguyên văn
- Evidence trace waterfall: [evidence/trace-waterfall.png](evidence/trace-waterfall.png) hoặc Langfuse UI project `cmso2esyq03rrad0cmgtfriqp`
- Giải thích một span đáng chú ý: span LLM generation ghi `prompt_name`, `prompt_label`, `prompt_version`, `prompt_source` giúp truy vết request dùng prompt nào

## 4. Prompt versioning

- Prompt name: `day13-chat`
- Version/label baseline: v1 — labels `baseline`, `production`
- Version/label candidate: v2 — label `candidate` (thêm "giữ câu trả lời dưới 3 câu + trích dẫn tên doc")
- Trace ID của mỗi version:
  - baseline v1: `33dd1336383f86673bb6b02afd42df01`, `e86e23bf3974b4bc1312511f48684978`, `9511ebe2b40c04bc73426f9d991123c7`
  - candidate v2: `f555d062c9e98740ada1ef8c05a739cf`, `b17ee7062f9b2c69a86bb3281ae5a667`, `4a0b01ecba27ad87fe46f59fac43066a`
  - production v2 (trước rollback): `c7afd50a6fa4b528c25e32a0ee4e9662`
  - production v1 (sau rollback): `877adb2c47ed5ff66d6e4ec76f71df39`
- Bằng chứng đổi label hoặc rollback: [evidence/prompt_versioning.txt](evidence/prompt_versioning.txt) — đã chuyển `production` sang v2 rồi rollback về v1, có trace minh chứng từng trạng thái

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: `HỢP LỆ: 6/6 panel có trong dashboard contract.` — [evidence/validate_dashboard_result.txt](evidence/validate_dashboard_result.txt)
- Evidence dashboard: [evidence/dashboard.html](evidence/dashboard.html), [evidence/dashboard.png](evidence/dashboard.png) — 6 panel: latency P50/P95/P99, traffic, errors+breakdown, cost, tokens, quality, mỗi panel có threshold, time range 60 phút, auto-refresh 30s
- SLO đã chọn: `latency_p95 <= 3000ms`, `error_rate <= 2%`, `quality >= 0.75`; ngưỡng lấy từ contract dashboard nên đo được liên tục
- Alert rules và runbook: [config/alert_rules.yaml](../config/alert_rules.yaml) + [docs/alerts.md](../docs/alerts.md)

## 6. Điều tra challenge

- Challenge ID: `day13-k3-observability-v1` (cohort K3, incident `rag_slow`, feature ảnh hưởng `refund`) — [evidence/challenge-investigation-rag_slow.json](evidence/challenge-investigation-rag_slow.json)
- Triệu chứng từ metrics: latency baseline ~157ms/request → ~2,651-2,694ms/request sau khi bật incident (tăng ~17 lần), P95 vượt hẳn `latency_threshold_ms=2000`. Ảnh: [evidence/dashboard-challenge-rag_slow.png](evidence/dashboard-challenge-rag_slow.png)
- Trace ID liên quan: cả 5 trace của 5 câu hỏi challenge đều bị ảnh hưởng đồng đều (~2.652s), khớp 1:1 với `correlation_id` qua metadata trace:
  - `k3-challenge-s01`: trace `382a9d68f9bf7aa78c9fe24b360899fc` / correlation `req-5424fd31`
  - `k3-challenge-s02`: trace `1c3c2b11b03dcf51e30c88cb00aa18b1` / correlation `req-e38b5811`
  - `k3-challenge-s03`: trace `d1c849237847bf48f3d50bbb5c05a2aa` / correlation `req-6cbd99b1`
  - `k3-challenge-s04`: trace `70f18c64a47b48676c2da39e2aaf4d78` / correlation `req-0c78982d`
  - `k3-challenge-s05`: trace `303fe93d342e38911137e1f256834550` / correlation `req-8af43641`
  - Lưu ý: mỗi trace chỉ có 1 span `run` gộp chung RAG + LLM, không tách span riêng
- Log line/correlation ID: `{"event":"response_sent","latency_ms":2651,"correlation_id":"req-5424fd31","session_id":"k3-challenge-s01","feature":"refund"}` — đầy đủ trong [evidence/challenge-investigation-rag_slow.json](evidence/challenge-investigation-rag_slow.json)
- Root cause: `app/mock_rag.py` dòng 18 — hàm `retrieve()` gọi `time.sleep(2.5)` khi `STATE["rag_slow"]` được bật, cộng thêm ~2.5s vào mọi request dùng RAG retrieval
- Fix action: tắt incident bằng `scripts/inject_incident.py --scenario rag_slow --disable` (hệ thống về latency baseline ~157ms). Về lâu dài: thêm timeout/circuit breaker cho bước `retrieve()`
- Preventive measure: thêm alert theo dõi P95 latency của feature dùng RAG vượt 2000ms; tách span RAG retrieval riêng trong `app/agent.py` để trace waterfall chỉ thẳng vào bước chậm

## 7. Đóng góp cá nhân

| Thành viên | Phần việc | Commit |
|---|---|---|
| Bùi Linh Đan (01177) | **CP1** — Middleware, correlation ID, JSON logging | `b61a0bd` |
| Lại Thế Rin (01665) | **CP1** — PII patterns, scrub_event, error_rate metrics | `c84e992` |
| Trương Thảo Nguyên (01389) | **CP2** — Langfuse, dashboard, alerts | `ac074c6` |
| Cao Thị Thu Trang (01885) | **CP2** — Prompt versioning, SLO, validation | `b82f4c0` |
| Bùi Thị Như Ngọc (01882) | **CP3** — Streamlit dashboard, investigation | `bf11ac3` |
| Trần Dương Tuấn (01271) | **CP3** — Challenge traces, fix, audit | `b82f4c0` |
