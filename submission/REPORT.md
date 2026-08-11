# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm:
- Repository URL:
- Commit SHA cuối:
- Thành viên và vai trò:

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: 100/100 (sau CP1; baseline 30/100 — [evidence/validate_logs_baseline.txt](evidence/validate_logs_baseline.txt))
- Tổng số traces: 115 (đếm qua Langfuse API, [evidence/traces_list.txt](evidence/traces_list.txt))
- Số PII leak còn lại: 0
- Link/đường dẫn dashboard: [submission/evidence/dashboard.html](evidence/dashboard.html) + ảnh [evidence/dashboard.png](evidence/dashboard.png) (self-hosted HTML)

## 3. Logging và tracing

- Evidence correlation ID: [evidence/cp1_log_evidence.txt](evidence/cp1_log_evidence.txt) — log `request_received` có `correlation_id: req-1ead3d37` + metadata `user_id_hash`, `session_id`, `feature`, `model`, `env`
- Evidence PII redaction: [evidence/cp1_log_evidence.txt](evidence/cp1_log_evidence.txt) — `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, `[REDACTED_CREDIT_CARD]` không xuất hiện nguyên văn
- Evidence trace waterfall: xem trong Langfuse UI project `cmso2esyq03rrad0cmgtfriqp`
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
- SLO đã chọn và lý do: theo `config/slo.yaml` — `latency_p95 <= 3000ms`, `error_rate <= 2%`, `quality >= 0.75`; ngưỡng lấy từ contract dashboard nên đo được liên tục
- Alert rules và runbook: [config/alert_rules.yaml](../config/alert_rules.yaml) + [docs/alerts.md](../docs/alerts.md)

## 6. Điều tra challenge

- Challenge ID:
- Triệu chứng từ metrics:
- Trace ID liên quan:
- Log line/correlation ID liên quan:
- Root cause:
- Fix action:
- Preventive measure:

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| | | | |
