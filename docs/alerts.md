# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: `high_latency_p95`
- Severity: warning
- SLI/SLO liên quan: `latency_p95_ms`, SLO target 99.5% trong 28 ngày
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000` kéo dài 5 phút
- Ảnh hưởng tới người dùng: trải nghiệm chat chậm, timeout ở client
- Ba bước kiểm tra đầu tiên:
  1. Mở trace chậm nhất trong Langfuse, tìm span tốn thời gian nhất (LLM generation hay RAG retrieval).
  2. Dùng correlation ID trong trace tìm log tương ứng trong `data/logs.jsonl`.
  3. Kiểm tra incidents đang bật: `curl /health` xem `rag_slow`.
- Mitigation tạm thời: giảm concurrency, disable incident, tăng timeout
- Owner: dashboard-team

## Alert 2

- Tên: `high_error_rate`
- Severity: critical
- SLI/SLO liên quan: `error_rate_pct`, SLO target 99.0%
- Điều kiện và thời gian duy trì: `error_rate_pct > 2` kéo dài 5 phút
- Ảnh hưởng tới người dùng: request thất bại trả về 500
- Ba bước kiểm tra đầu tiên:
  1. Xem error breakdown trên dashboard, xác định `error_type` nào chiếm đa số.
  2. Tìm log `request_failed` có cùng `error_type` và correlation ID.
  3. Kiểm tra dependency: Langfuse, mock_rag, model config.
- Mitigation tạm thời: rollback code mới nhất, disable incident gây lỗi
- Owner: dashboard-team

## Alert 3

- Tên: `low_quality_score`
- Severity: warning
- SLI/SLO liên quan: `quality_score_avg`, SLO target 95.0%
- Điều kiện và thời gian duy trì: `mean(quality_score) < 0.75` kéo dài 15 phút
- Ảnh hưởng tới người dùng: câu trả lời kém chất lượng, không dùng được context
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra prompt version hiện tại của `production` trong Langfuse.
  2. Xem trace của các request có quality thấp, so sánh `prompt_label`/`prompt_version`.
  3. So sánh với baseline: nếu vừa đổi label/rollback prompt thì cân nhắc rollback.
- Mitigation tạm thời: rollback `production` về prompt version trước đó
- Owner: dashboard-team
