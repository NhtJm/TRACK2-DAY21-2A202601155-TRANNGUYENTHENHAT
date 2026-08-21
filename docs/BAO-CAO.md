# Báo cáo Lab MLOps Day 21 — Wine Quality CI/CD Pipeline

**Repo:** NhtJm/TRACK2-DAY21-2A202601155-TRANNGUYENTHENHAT · **Cloud:** GCP (`kis-check-aic`) · **Ngày:** 2026-08-21
**Báo cáo đầy đủ (HTML, có log/bảng/sơ đồ):** xem `docs/report.html` (đã publish, link trong hội thoại giao bài).

## 1. Bộ siêu tham số đã chọn và lý do

Grid-search 15 lần chạy trên MLflow (`sqlite:///mlflow.db`), trải trên 3 thuật toán (`random_forest`,
`gradient_boosting`, `logistic_regression`). Cấu hình tốt nhất:

```
model_type: random_forest
n_estimators: 300
max_depth: null       # không giới hạn độ sâu
min_samples_split: 2
```

→ **accuracy = 0.682, f1_score (weighted) = 0.6811** trên `data/eval.csv` (500 mẫu, tách riêng từ đầu).

Lý do chọn: tăng `n_estimators` và bỏ trần `max_depth` cải thiện rõ rệt so với baseline mặc định
(`n_estimators=100, max_depth=5` → chỉ 0.564) vì cây sâu hơn nắm được ranh giới phi tuyến giữa 3 lớp
chất lượng rượu. Sau ngưỡng này (n_estimators 400–600, đổi `max_features`/`class_weight`/`bootstrap`),
accuracy bão hòa quanh 0.67–0.68 — không cấu hình nào trong 15 lần chạy vượt được. Gradient boosting
đạt xấp xỉ (0.674), logistic regression thấp hơn hẳn (0.568), phù hợp với đặc điểm dữ liệu phi tuyến,
nhãn có nhiễu chủ quan (điểm "quality" do con người chấm).

## 2. Khó khăn gặp phải và cách giải quyết

**(a) Ngưỡng eval gate 0.70 không đạt được chỉ với `train_phase1.csv` (2998 mẫu).** Đã thử mở rộng
grid-search (15 cấu hình, 3 thuật toán) nhưng tốt nhất chỉ 0.682. Xác minh bằng cách train thử trên
tập gộp cả `train_phase2.csv` (5996 mẫu, mô phỏng Bước 3) → accuracy đạt **0.746**, vượt ngưỡng rõ
ràng. Kết luận: đây là giới hạn thật của bài toán với lượng dữ liệu ít, không phải lỗi cấu hình —
Eval gate chặn deploy ở vòng CI đầu tiên (Bước 2) là hành vi **đúng thiết kế**, và Bước 3 (continuous
training với dữ liệu mới) chính là nơi vượt ngưỡng, đúng tinh thần sư phạm của bài lab.

**(b) Môi trường thực thi không có sẵn `gcloud`/`gh` CLI như dự kiến ban đầu, Python hệ thống
không tương thích các bản pin trong `requirements.txt`.** Cài đặt cả hai CLI vào thư mục người dùng
(không cần quyền root), dùng `uv` để lấy Python 3.10 chuẩn khớp phiên bản CI, tạo virtualenv riêng.

**(c) `.dvc/config` mặc định lưu đường dẫn credential tuyệt đối của máy local.** Nếu commit nguyên
trạng, `dvc pull` trên GitHub Actions runner sẽ fail vì đường dẫn đó không tồn tại trên runner. Xử lý:
chuyển `credentialpath` sang `.dvc/config.local` (không commit); CI dùng biến môi trường
`GOOGLE_APPLICATION_CREDENTIALS` như thiết kế gốc của `mlops.yml`.

**(d) Token GitHub CLI thiếu scope `workflow`** khi mới đăng nhập, cần cấp thêm quyền qua
`gh auth refresh -s workflow` mới push được thay đổi vào `.github/workflows/mlops.yml`.

## 3. Kết quả pipeline (tóm tắt)

- MLflow: 15 lần chạy, đủ `accuracy` + `f1_score` mỗi lần (§04 báo cáo HTML).
- DVC: remote GCS đã cấu hình, `dvc push` thành công 3 file dữ liệu (§05).
- CI/CD 4 job (Test/Train/Eval/Deploy), VM FastAPI, demo eval-gate-fail, Bước 3 continuous training,
  và 5 bonus: xem trạng thái cập nhật theo thời gian thực trong `docs/report.html`.

## 4. Bonus đã thực hiện

Đa thuật toán (so sánh 3 model_type trên MLflow), Báo cáo tự động (`classification_report` +
confusion matrix ra `outputs/report.txt`), Rollback an toàn (đọc `metrics.json` cũ trên GCS trước khi
ghi đè, chỉ deploy khi accuracy mới ≥ cũ), Cảnh báo lệch dữ liệu (demo trên tập lệch thủ công vì phân
phối nhãn thật 36/44/20% không bao giờ kích hoạt cảnh báo). DagsHub remote tracking: hook sẵn trong
`mlops.yml`, kích hoạt khi có thông tin đăng nhập DagsHub.
