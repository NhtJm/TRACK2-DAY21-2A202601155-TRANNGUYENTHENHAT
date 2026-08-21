# Báo cáo Lab MLOps Day 21 — Wine Quality CI/CD Pipeline

**Repo:** [NhtJm/TRACK2-DAY21-2A202601155-TRANNGUYENTHENHAT](https://github.com/NhtJm/TRACK2-DAY21-2A202601155-TRANNGUYENTHENHAT) · **Cloud:** GCP `kis-check-aic` · **VM:** 35.239.63.30:8000
**Báo cáo đầy đủ (log CI, sơ đồ, tự chấm rubric):** `docs/report.html` · **Ảnh:** `docs/screenshots/`

## 1. Siêu tham số đã chọn và lý do

Grid-search **15 lần chạy** trên MLflow, trải 3 thuật toán (`random_forest`, `gradient_boosting`, `logistic_regression`). Cấu hình tốt nhất:

```yaml
model_type: random_forest    # n_estimators: 300, max_depth: null, min_samples_split: 2
```

**Lý do:** baseline mặc định (`n_estimators=100, max_depth=5`) chỉ đạt **0.564**. Bỏ trần `max_depth` và nâng `n_estimators` lên 300 đưa accuracy lên **0.686** — cây sâu hơn nắm được ranh giới phi tuyến giữa 3 lớp chất lượng. Sau mốc này accuracy bão hòa: `n_estimators` 400/500/600 cho 0.678/0.680/0.676, đổi `class_weight` hay `max_features` đều không vượt được. `gradient_boosting` xấp xỉ (0.674), `logistic_regression` thấp hẳn (0.568) — phù hợp với dữ liệu phi tuyến, nhãn có nhiễu chủ quan do người chấm.

## 2. So sánh Bước 2 (2.998 mẫu) và Bước 3 (5.996 mẫu)

Cùng bộ siêu tham số, chỉ khác lượng dữ liệu huấn luyện; đánh giá trên cùng `data/eval.csv` (500 mẫu held-out):

| Chỉ số | Bước 2 — 2.998 mẫu | Bước 3 — 5.996 mẫu | Chênh lệch |
|---|---|---|---|
| accuracy | 0.6820 | **0.7460** | **+0.0640** |
| f1_score (weighted) | 0.6811 | **0.7449** | **+0.0638** |
| Eval gate (≥ 0.70) | ❌ Chặn deploy | ✅ Cho deploy | — |

**Nhận xét:** gấp đôi dữ liệu cải thiện accuracy 6.4 điểm phần trăm — đủ để vượt ngưỡng 0.70. Điều này chứng minh đúng luận điểm của continuous training: dữ liệu mới, chứ không phải tinh chỉnh siêu tham số, mới là thứ phá được trần hiệu năng ở đây.

## 3. Khó khăn và cách giải quyết

**(a) Ngưỡng eval gate 0.70 không đạt được với 2.998 mẫu.** Mở rộng grid-search lên 15 cấu hình/3 thuật toán, tốt nhất vẫn chỉ 0.682. Kết luận đây là giới hạn thật của bài toán ở lượng dữ liệu đó, không phải lỗi cấu hình — và eval gate chặn deploy ở mốc Bước 2 là **hành vi đúng thiết kế**. Bước 3 mới là nơi vượt ngưỡng (0.746).

**(b) `git push` không kích hoạt được GitHub Actions.** Triệu chứng ban đầu bị chẩn đoán nhầm là sai `paths` filter; sửa `data/**.dvc` → `data/**` vẫn không có run nào được tạo. Xác minh bằng cách bỏ hẳn path filter rồi push file nằm đúng trong filter — vẫn 0 run. **Nguyên nhân thật: repo là fork, GitHub mặc định tắt workflow chạy theo `push` trên repo fork** (nhưng vẫn cho `workflow_dispatch`, nên ban đầu tưởng pipeline đã chạy đúng). Khắc phục: bật thủ công trong tab Actions. Sau đó run #6 chạy với `event=push`, tên run là commit dữ liệu, cả 4 job xanh — Bước 3 zero-touch đã xác minh.

**(c) `.dvc/config` lưu `credentialpath` tuyệt đối của máy local.** Nếu commit nguyên trạng, `dvc pull` trên runner sẽ fail. Chuyển sang `.dvc/config.local` (không commit); CI dùng biến `GOOGLE_APPLICATION_CREDENTIALS`.

**(d) Mất toàn bộ lịch sử MLflow khi dựng lại môi trường** (`mlflow.db` nằm trong `.gitignore`). Phải train lại 15 thí nghiệm. Đây chính là lý do Bonus 1 (tracking từ xa trên DagsHub) có giá trị thực tế: từ đó mọi run CI được ghi lên server, đổi máy không mất dữ liệu.

## 4. Bonus đã thực hiện (5/5)

| # | Bonus | Bằng chứng |
|---|---|---|
| 1 | MLflow remote tracking trên DagsHub | `docs/evidence/bonus1-dagshub-verify.txt` — CI ghi run acc=0.746 lên server |
| 2 | Đa thuật toán (`model_type`) | 3 thuật toán trên MLflow Compare, `docs/screenshots/01b` |
| 3 | Báo cáo tự động | `classification_report` + confusion matrix → `outputs/report.txt` |
| 4 | Rollback an toàn | So accuracy mới vs model đang chạy trên GCS trước khi ghi đè |
| 5 | Cảnh báo lệch dữ liệu | Ghi `label_distribution` vào `metrics.json`; demo trên tập lệch |
