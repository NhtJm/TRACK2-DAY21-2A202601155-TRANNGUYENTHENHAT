# KẾ HOẠCH THỰC HIỆN — Lab MLOps Day 21 (TRACK2-DAY21-2A202601155)

> Trạng thái: **PLAN — chưa thực thi**. Chờ duyệt trước khi chạy.
> Ngày lập: 2026-08-21 · Repo: `NhtJm/TRACK2-DAY21-2A202601155-TRANNGUYENTHENHAT` (public)

---

## 0. Khảo sát hiện trạng repo

### 0.1 Những gì ĐÃ có (không cần viết lại)
| File | Trạng thái |
|---|---|
| `README.md`, `tasks/buoc-{1,2,3}.md` | Hướng dẫn đầy đủ + rubric + 5 bonus |
| `generate_data.py` | Hoàn chỉnh — tải Wine Quality từ UCI, chia 2998/500/2998 |
| `add_new_data.py` | Hoàn chỉnh — ghép phase2 vào phase1 (2998 → 5996) |
| `params.yaml` | Có sẵn `n_estimators=100, max_depth=5, min_samples_split=2` |
| `requirements.txt` | Pin đầy đủ, đã chọn `dvc[gs]` + `google-cloud-storage` → **GCP** |
| `.gitignore` | Đã ignore `models/`, `outputs/`, `data/*.csv`, `sa-key.json`, `mlflow.db` |
| `src/__init__.py`, `tests/__init__.py` | Đã tồn tại (rỗng) — import package OK |

### 0.2 Những gì CHƯA có — 35 TODO cần điền
| File | Số TODO | Nội dung |
|---|---|---|
| `src/train.py` | 10 | Đọc data → tách X/y → MLflow run → fit RF → metric → log → dump `metrics.json` + `model.pkl` → return acc |
| `tests/test_train.py` | 9 | Fixture data ngẫu nhiên + 3 test (return float, metrics.json, model.pkl) |
| `src/serve.py` | 8 | `download_model()` từ GCS + `GET /health` + `POST /predict` (12 features → 0/1/2) |
| `.github/workflows/mlops.yml` | 8 | pytest cmd, auth GCS, `dvc pull`, read metrics → output, upload model, eval gate, SSH restart + health check |

### 0.3 Hạ tầng chưa tồn tại
GCS bucket · Service Account + key · DVC remote (`.dvc/` chưa init) · GCE VM `mlops-serve` + firewall 8000 · SSH deploy key · 5 GitHub Secrets.

---

## 1. Phát hiện kỹ thuật quan trọng (đọc trước khi chạy)

### ⚠️ R1 — Accuracy có thể KHÔNG đạt ngưỡng 0.70 với params mặc định
Wine Quality 3 lớp (thấp/TB/cao) là bài toán khó. `max_depth=5` thường chỉ cho **~0.55–0.60 accuracy** → **eval gate 0.70 sẽ chặn deploy**, hỏng cả Bước 2 và 3 (28 điểm).

**Đây chính là lý do Bước 1 tồn tại**: phải grid-search thật để tìm bộ params vượt 0.70, không phải chạy 3 lần cho có.
- Hướng: `max_depth: null` (không giới hạn) + `n_estimators: 200–300` → RF thường đạt **0.68–0.72**.
- Bonus 2 (`gradient_boosting`) là **phương án dự phòng** nếu RF không qua nổi.
- Nếu sau grid-search vẫn < 0.70 → báo cáo trung thực + minh chứng eval gate hoạt động đúng (chặn deploy), rồi dùng model tốt nhất; đồng thời trình bày số liệu để giảng viên thấy ngưỡng 0.70 là ràng buộc của đề, không phải lỗi triển khai.

### ⚠️ R2 — Bonus 2 làm vỡ `RandomForestClassifier(**params)`
Thêm `model_type` vào `params.yaml` rồi truyền thẳng `**params` sẽ raise `TypeError: unexpected keyword 'model_type'`.
→ Thiết kế: `model_type = params.pop("model_type", "random_forest")` (trên **bản copy** của dict, vì `params` đã được `mlflow.log_params()` và test truyền dict không có key này).

### ⚠️ R3 — Test ghi vào CWD, dùng chung state
3 test đều ghi `outputs/metrics.json` và `models/model.pkl` ở thư mục hiện tại (không phải `tmp_path`). Đúng theo khung đề bài nên **giữ nguyên**, nhưng phải đảm bảo chạy tuần tự (mặc định pytest) và không bật `pytest-xdist`.

### ⚠️ R4 — `mlflow.sklearn.log_model` làm CI chậm
Mỗi lần gọi mất ~10–30 s (infer signature + resolve pip requirements). 3 test × 3 lần = có thể +90 s cho job Test. Chấp nhận được, nhưng nếu job Test > 10 phút sẽ set `MLFLOW_TRACKING_URI=file:./mlruns` và cân nhắc bỏ log_model trong đường test.

### ⚠️ R5 — Bonus 5 sẽ KHÔNG bao giờ in cảnh báo với data thật
Phân phối nhãn Wine Quality ≈ 37% / 44% / 20% — không lớp nào < 10%, nên logic cảnh báo không bao giờ kích hoạt → không có bằng chứng chấm điểm.
→ Phải tạo **run demo riêng** trên tập con lệch (ví dụ `data/train_skewed.csv` chỉ giữ 5% lớp 2) để chụp log cảnh báo.

### ⚠️ R6 — Thứ tự demo eval gate rất quan trọng
Rubric cần **cả hai**: 4 job xanh (16đ) **và** deploy bị chặn khi acc < 0.70 (4đ). Một run đỏ trên `main` làm xấu tab Actions.
→ Chạy demo fail bằng `workflow_dispatch` trên nhánh riêng `demo/eval-gate-fail` với input `threshold=0.99`. Lịch sử `main` vẫn toàn xanh.

### ⚠️ R7 — Bonus 4 phụ thuộc thứ tự đọc/ghi
Rollback phải **đọc** `metrics.json` cũ từ GCS **TRƯỚC**, so sánh, rồi mới **ghi đè** metrics mới lên GCS. Đảo thứ tự → luôn tự so với chính mình.

### ⚠️ R8 — Compute Engine API chưa bật
`compute.googleapis.com` chưa enable trên `kis-check-aic`. Cần `gcloud services enable compute.googleapis.com` (~1–2 phút) và project phải có billing active. VM `e2-small` ≈ **$0.017/giờ** (~$0.10 cho cả lab). **Bắt buộc xóa VM sau khi nộp bài.**

### ⚠️ R9 — Python local 3.11 vs CI 3.10
`scikit-learn==1.4.2` có wheel cho cả hai → model pickle tương thích. Nhưng **VM cũng phải dùng scikit-learn 1.4.2**, nếu không `joblib.load` sẽ cảnh báo/lỗi version mismatch. → Pin phiên bản khi cài trên VM.

---

## 2. Chiến lược ghi bằng chứng (yêu cầu: run logs + full command output + HTML)

Mọi lệnh chạy qua wrapper ghi log:
```bash
run() { echo "\$ $*" | tee -a "$LOG"; "$@" 2>&1 | tee -a "$LOG"; }
```
Cấu trúc bằng chứng sinh ra:
```
docs/
├── PLAN.md                     <- file này
├── report.html                 <- BÁO CÁO HTML (deliverable chính)
├── logs/
│   ├── 00-env.log              <- version tooling, auth status
│   ├── 01-setup.log            <- venv + pip install + generate_data.py
│   ├── 02-mlflow-runs.log      <- 5+ lần train, đầy đủ stdout
│   ├── 03-gcs-dvc.log          <- tạo bucket, SA, dvc init/add/push
│   ├── 04-pytest.log           <- pytest -v output
│   ├── 05-vm-setup.log         <- tạo VM, firewall, scp, systemd
│   ├── 06-ci-run-1.log         <- gh run view --log (Bước 2, 4 job xanh)
│   ├── 07-eval-gate-fail.log   <- demo gate chặn deploy
│   ├── 08-curl-endpoints.log   <- /health + /predict
│   ├── 09-ci-run-2.log         <- Bước 3, trigger bởi commit data
│   ├── 10-bonus-*.log          <- log từng bonus
│   └── 99-cleanup.log          <- xóa VM
├── evidence/
│   ├── mlflow-runs.csv         <- bảng so sánh 5 run xuất từ mlflow
│   ├── metrics-step2.json      <- artifact tải từ CI run 1
│   ├── metrics-step3.json      <- artifact tải từ CI run 2
│   └── report.txt              <- Bonus 3 confusion matrix
└── screenshots/                <- ảnh chụp MLflow UI, Actions, GCS Console
```

**`docs/report.html`** — trang tự chứa (inline CSS/JS, không CDN), theme-aware, gồm:
1. Sơ đồ kiến trúc (inline SVG) — luồng local → GitHub → Actions 4 job → GCS/VM
2. Giải thích từng đoạn code đã viết + **lý do** thiết kế
3. Bảng so sánh 5 thí nghiệm MLflow + kết luận chọn params
4. Timeline pipeline + trích log thật của từng job
5. Bảng đối chiếu Bước 2 (2998 mẫu) vs Bước 3 (5996 mẫu)
6. 5 bonus, mỗi phần: yêu cầu → code → log chứng minh
7. Bảng tự chấm theo rubric 100 điểm
8. Nhật ký sự cố & cách xử lý
→ Publish thành Artifact (link riêng tư, chia sẻ được).

---

## 3. Các giai đoạn thực hiện

### GĐ 0 — Môi trường & baseline  (~15 phút)
1. `python3 -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt` (nặng nhất: mlflow + dvc, ~5–8 phút)
3. `python generate_data.py` → verify `2998 / 500 / 2998`
4. `wc -l data/*.csv`, `head -2` để chốt schema 12 feature + `target`
5. Ghi `docs/logs/00-env.log`, `01-setup.log`
**DoD:** 3 file CSV đúng số dòng; `pip list` khớp requirements.

### GĐ 1 — Bước 1: MLflow tracking  (~35 phút) — 24 điểm
1. Viết `src/train.py` (10 TODO), thiết kế sẵn cho Bonus 2/3/5:
   - `train(params, data_path, eval_path) -> float`
   - `mlflow.log_params` → fit → `accuracy_score` + `f1_score(average="weighted")`
   - `mlflow.sklearn.log_model` + `mlflow.set_tag("run_name", ...)`
   - ghi `outputs/metrics.json`, `models/model.pkl`, `return float(acc)`
2. `export MLFLOW_TRACKING_URI=sqlite:///mlflow.db`
3. Chạy **5 thí nghiệm** (vượt yêu cầu 3):

   | # | n_estimators | max_depth | min_samples_split | Kỳ vọng |
   |---|---|---|---|---|
   | 1 | 100 | 5 | 2 | baseline (~0.57) |
   | 2 | 50 | 3 | 2 | underfit (~0.53) |
   | 3 | 200 | 10 | 5 | (~0.65) |
   | 4 | 300 | null | 2 | **ứng viên tốt nhất (~0.70)** |
   | 5 | 200 | 20 | 5 | (~0.69) |

4. Xuất bảng so sánh: `mlflow runs list` / query sqlite → `docs/evidence/mlflow-runs.csv`
5. `mlflow ui --backend-store-uri sqlite:///mlflow.db` → chụp màn hình (sort theo accuracy, Compare view)
6. **Ghi params tốt nhất vào `params.yaml`**
**DoD:** ≥3 run có params khác nhau, mỗi run đủ `accuracy` + `f1_score`; params.yaml đã cập nhật; có phân tích bằng chữ.
**Gate:** nếu run tốt nhất < 0.70 → kích hoạt Bonus 2 sớm, thử `gradient_boosting`.

### GĐ 2 — Bước 2A: Unit test  (~20 phút)
1. Viết `tests/test_train.py` (9 TODO) đúng khung: `rng = np.random.default_rng(0)`, n=200, split 160/40
2. `pytest tests/ -v` → 3 passed
**DoD:** 3/3 xanh, log đầy đủ vào `04-pytest.log`.

### GĐ 3 — Bước 2B: GCS + DVC  (~25 phút) — 12 điểm
1. `export PROJECT=kis-check-aic BUCKET=mlops-lab-<suffix-duy-nhất>`
2. `gsutil mb -p $PROJECT -l us-central1 gs://$BUCKET`
3. `gcloud iam service-accounts create mlops-lab-sa` → `gsutil iam ch ...objectAdmin gs://$BUCKET` (least privilege, **không** dùng `storage.admin`)
4. `gcloud iam service-accounts keys create sa-key.json`
5. `dvc init` → `dvc remote add -d myremote gs://$BUCKET/dvc` → `dvc remote modify myremote credentialpath sa-key.json`
6. `dvc add data/{train_phase1,eval,train_phase2}.csv` → `dvc push`
7. `gsutil ls -r gs://$BUCKET/dvc | head -20` → bằng chứng file đã lên cloud
8. Commit `.dvc/config` + 3 file `.dvc` (⚠️ **không** commit CSV)
**DoD:** `dvc push` OK; `gsutil ls` liệt kê object; `git log --name-only` không thấy `.csv`.
**⚠️ Kiểm tra bảo mật:** `git status` phải KHÔNG bao giờ thấy `sa-key.json`.

### GĐ 4 — Bước 2C: serve.py + VM  (~40 phút) — 12 điểm
1. Viết `src/serve.py` (8 TODO): `download_model()` từ GCS, `/health` → `{"status":"ok"}`, `/predict` validate đúng 12 feature (else HTTP 400) → `{"prediction":int, "label":"thap|trung_binh|cao"}`
2. Test local: `GCS_BUCKET=$BUCKET uvicorn src.serve:app` → curl thử (sau khi có model trên GCS)
3. `gcloud services enable compute.googleapis.com` (R8)
4. `gcloud compute instances create mlops-serve --zone=us-central1-a --machine-type=e2-small --image-family=ubuntu-2204-lts ...`
5. Firewall `allow-mlops-serve` tcp:8000 (target-tags, không mở toàn project)
6. SSH cài: `pip3 install fastapi uvicorn scikit-learn==1.4.2 joblib google-cloud-storage` (⚠️ pin theo R9)
7. `scp sa-key.json` + `src/serve.py` lên VM; tạo systemd unit; `systemctl enable` (**chưa start** — model chưa có trên GCS)
**DoD:** VM RUNNING, có IP public, `systemctl is-enabled mlops-serve` = enabled.

### GĐ 5 — Bước 2D: CI/CD pipeline  (~55 phút) — 16 điểm
1. Tạo SSH deploy key `ssh-keygen -t ed25519 -f ~/.ssh/mlops_deploy -N ""` → thêm vào `authorized_keys` của VM
2. Set 5 secrets qua `gh secret set`: `CLOUD_CREDENTIALS`, `CLOUD_BUCKET`, `VM_HOST`, `VM_USER`, `VM_SSH_KEY`
3. Điền 8 TODO trong `mlops.yml`:
   - Job Test: `pytest tests/ -v`
   - Job Train: ghi credentials → `$GITHUB_ENV`; `dvc pull data/train_phase1.csv.dvc data/eval.csv.dvc`; train; đọc accuracy → `$GITHUB_OUTPUT`; upload `model.pkl` → `gs://$BUCKET/models/latest/model.pkl`; upload artifact
   - Job Eval: `float()` accuracy (⚠️ output là string — lỗi phổ biến nêu trong troubleshooting) → `SystemExit` nếu < 0.70
   - Job Deploy: `sudo systemctl restart mlops-serve` → retry loop curl `/health` → `exit 1` nếu fail
4. `git push origin main` → theo dõi `gh run watch`
5. **Dự kiến 2–4 vòng sửa lỗi CI** (mỗi run ~6–9 phút) — đây là phần tốn thời gian nhất
6. Sau khi model lên GCS: `gcloud compute ssh mlops-serve --command "sudo systemctl start mlops-serve"`
7. `curl http://$VM_IP:8000/health` và `curl -X POST .../predict` với 12 feature mẫu
8. `gh run view <id> --log > docs/logs/06-ci-run-1.log`
**DoD:** 4 job xanh; `/health` trả `{"status":"ok"}`; `/predict` trả prediction + label hợp lệ; GCS có `models/latest/model.pkl`.

### GĐ 6 — Demo eval gate chặn deploy  (~15 phút) — 4 điểm
1. Thêm input `threshold` vào `workflow_dispatch` (mặc định `0.70`) — không đổi hành vi push
2. Nhánh `demo/eval-gate-fail` → `gh workflow run mlops.yml --ref demo/eval-gate-fail -f threshold=0.99`
3. Kết quả kỳ vọng: Test ✅ · Train ✅ · **Eval ❌** · Deploy ⏭️ skipped
4. Lưu log + ảnh chụp; `main` vẫn giữ lịch sử toàn xanh (R6)
**DoD:** log Eval in rõ `FAILED: accuracy X < 0.99`, job Deploy hiển thị `skipped`.

### GĐ 7 — Bước 3: Continuous training  (~25 phút) — 12 điểm
1. `python add_new_data.py` → `2998 -> 5996`; `wc -l` = 5997
2. `dvc add data/train_phase1.csv` → `git add data/train_phase1.csv.dvc`
3. `git commit -m "data: bổ sung 2998 mẫu dữ liệu mới (train_phase2)"`
4. **`dvc push` TRƯỚC**, rồi mới `git push` (thứ tự bắt buộc — nếu ngược, CI `dvc pull` sẽ fail)
5. `git log --name-only -1` → xác nhận chỉ có `.dvc` (troubleshooting của đề)
6. `gh run watch` → 4 job xanh, tên run = đúng commit message dữ liệu
7. Tải artifact 2 run → điền bảng so sánh mục 3.6
8. `curl /predict` lại xác nhận model mới đang phục vụ
**DoD:** pipeline tự kích hoạt bởi commit dữ liệu (0 thao tác thủ công); bảng so sánh acc/f1 đã điền.

### GĐ 8 — BONUS (20 điểm)

| # | Bonus | Thời gian | Cách làm | Bằng chứng |
|---|---|---|---|---|
| 1 | DagsHub remote tracking (4đ) | ~25' | Tạo tài khoản DagsHub → connect repo → thêm secrets `MLFLOW_TRACKING_URI/USERNAME/PASSWORD` → `mlops.yml` export env cho job Train | Ảnh DagsHub Experiments hiện run từ CI + log CI |
| 2 | Đa thuật toán (4đ) | ~25' | `model_type` trong `params.yaml`; factory `random_forest`/`gradient_boosting`/`logistic_regression`; xử lý R2 (pop trên bản copy); LR cần `StandardScaler` trong Pipeline; chạy ≥2 thuật toán | Compare view MLflow ≥2 model_type + `mlflow-runs.csv` |
| 3 | Báo cáo tự động (4đ) | ~20' | `classification_report` + `confusion_matrix` dạng text → `outputs/report.txt`; thêm precision/recall từng lớp; `upload-artifact` kèm `metrics.json` | `docs/evidence/report.txt` + log CI + ảnh artifact |
| 4 | Rollback an toàn (4đ) | ~30' | Trước train: tải `gs://$BUCKET/models/latest/metrics.json` (nếu có) → so sánh acc mới vs cũ → chỉ upload/deploy khi `acc_new >= acc_old`; ghi rõ so sánh vào log (⚠️ thứ tự R7) | Log 2 kịch bản: (a) acc cao hơn → deploy, (b) acc thấp hơn → chặn |
| 5 | Cảnh báo drift (4đ) | ~20' | Tính tỷ lệ nhãn trước train; lớp nào < 10% → in `WARNING` rõ ràng; ghi `label_distribution` vào `metrics.json` cạnh accuracy/f1 | Log run thật (không cảnh báo) + run demo trên tập lệch (có cảnh báo) — xử lý R5 |

**Lưu ý Bonus 1:** cần **tài khoản DagsHub** — đây là điểm duy nhất cần thao tác của bạn. Nếu không muốn đăng ký, phương án thay thế: dựng MLflow server ngay trên VM `mlops-serve` (port 5000) và trỏ CI vào đó — vẫn đạt đúng tinh thần "tracking từ xa, xem được từ bất cứ đâu".

### GĐ 9 — Báo cáo & bàn giao  (~50 phút)
1. Tổng hợp toàn bộ log → `docs/report.html` (self-contained, theme-aware, có SVG kiến trúc)
2. Publish thành Artifact → link chia sẻ
3. `docs/BAO-CAO.md` — báo cáo ngắn ≤1 trang A4 theo yêu cầu nộp bài (params đã chọn + lý do, khó khăn & cách giải quyết)
4. Cập nhật `README.md` phần kết quả; commit toàn bộ evidence
5. **`gcloud compute instances delete mlops-serve`** — tránh phát sinh chi phí (ghi `99-cleanup.log`)
   - ⚠️ Chỉ xóa **SAU KHI** đã chụp đủ ảnh và nộp bài. Sẽ hỏi lại bạn trước khi xóa.

---

## 4. ƯỚC TÍNH THỜI GIAN

### 4.1 Theo giai đoạn

| GĐ | Nội dung | Điểm | Thời gian | Trong đó chờ máy |
|---|---|---|---|---|
| 0 | Môi trường & data | — | 15' | 8' (pip install) |
| 1 | Bước 1 — MLflow 5 run | 24 | 35' | 12' (train) |
| 2 | Unit test | (16) | 20' | 3' |
| 3 | GCS + DVC | 12 | 25' | 6' (dvc push) |
| 4 | serve.py + VM | 12 | 40' | 20' (tạo VM, pip trên e2-small) |
| 5 | CI/CD pipeline | 16 | 55' | 35' (2–4 vòng CI × 6–9') |
| 6 | Demo eval gate | 4 | 15' | 8' |
| 7 | Bước 3 — CT | 12 | 25' | 12' |
| 8 | Bonus 1–5 | 20 | 2h00' | 45' (CI re-run) |
| 9 | Báo cáo HTML + cleanup | — | 50' | 5' |
| — | **Buffer sự cố** (auth, quota, CI flake) | — | 40' | — |

### 4.2 Tổng cộng

| Kịch bản | Thời gian | Ghi chú |
|---|---|---|
| **Chỉ phần chính (GĐ 0–7)** → 80đ | **≈ 3h55'** | Bỏ bonus |
| **Toàn bộ kể cả bonus (GĐ 0–9)** → 100đ | **≈ 6h45'** | Ước tính chính, có buffer |
| Khoảng dao động thực tế | **5h30' – 8h30'** | Phụ thuộc số vòng sửa CI |
| Nếu bạn tự làm tay theo tasks/*.md | **10 – 14 giờ** | Lần đầu học MLOps |

**Phân bổ:** ~2h30' chờ máy (CI, pip, VM) — thời gian này chạy song song được với việc soạn báo cáo/HTML, nên có thể rút xuống ~5h30' nếu tối ưu.

**Đường găng (critical path):** GĐ 3 → 4 → 5 (GCS phải xong trước VM, VM phải xong trước CI Deploy). GĐ 1, 2 và phần khung HTML làm song song được ngay từ đầu.

### 4.3 Mốc kiểm tra
| Mốc | Sau | Điểm tích lũy |
|---|---|---|
| M1 — MLflow 5 run + params tốt nhất | ~50' | 24/100 |
| M2 — DVC push + 3 test xanh | ~1h35' | 36/100 |
| M3 — CI 4 job xanh + /predict OK | ~3h10' | 68/100 |
| M4 — Eval gate demo + Bước 3 xanh | ~3h55' | 80/100 |
| M5 — 5 bonus xong | ~5h55' | 100/100 |
| M6 — HTML + báo cáo + cleanup | ~6h45' | Sẵn sàng nộp |

### 4.4 Chi phí
| Khoản | Ước tính |
|---|---|
| GCE `e2-small` us-central1-a | $0.017/h × ~5h ≈ **$0.09** |
| GCS storage (~15 MB) + egress | < **$0.01** |
| GitHub Actions (repo public) | **Miễn phí** |
| **Tổng** | **< $0.15** (miễn là xóa VM sau khi xong) |

---

## 5. Ma trận rubric → bằng chứng

| Hạng mục | Điểm | GĐ | Bằng chứng nộp |
|---|---|---|---|
| B1 — MLflow ≥3 run khác params | 12 | 1 | `screenshots/mlflow-ui.png` + `evidence/mlflow-runs.csv` |
| B1 — Đủ accuracy + f1_score | 8 | 1 | `logs/02-mlflow-runs.log` |
| B1 — Phân tích params tốt nhất | 4 | 1 | `report.html` §3 + `BAO-CAO.md` |
| B2 — DVC remote + push | 12 | 3 | `logs/03-gcs-dvc.log` + `screenshots/gcs-console.png` |
| B2 — 4 job CI xanh | 16 | 5 | `logs/06-ci-run-1.log` + `screenshots/actions-step2.png` |
| B2 — Eval gate chặn deploy | 4 | 6 | `logs/07-eval-gate-fail.log` + screenshot |
| B2 — VM /predict đúng | 12 | 5 | `logs/08-curl-endpoints.log` |
| B3 — Commit data tự kích hoạt | 12 | 7 | `logs/09-ci-run-2.log` + `git log --name-only -1` |
| Bonus 1–5 | 20 | 8 | `logs/10-bonus-*.log` + screenshots |
| **Tổng** | **100** | | |

---

## 6. Câu hỏi cần bạn quyết trước khi chạy

1. **Cloud provider** — đề xuất **GCP** (`kis-check-aic`): gcloud đã auth, `requirements.txt` đã pin `dvc[gs]` + `google-cloud-storage`, README lấy GCP làm mặc định. (AWS cũng đã auth nếu bạn muốn đổi, nhưng phải sửa requirements.)
2. **Tạo VM GCE** — cần bật Compute Engine API + billing, chi phí < $0.15. Đồng ý?
3. **Bonus 1 (DagsHub)** — bạn có tài khoản DagsHub chưa, hay dùng phương án MLflow server tự dựng trên VM?

---

## 7. Quy tắc an toàn khi thực thi

- ❌ **KHÔNG** commit `sa-key.json`, private key, hay file CSV (kiểm tra `git status` trước mỗi commit)
- ❌ **KHÔNG** in nội dung secret ra log — mọi log sẽ được scan & redact trước khi đưa vào `report.html`
- ✅ Service Account chỉ `objectAdmin` trên đúng 1 bucket (không `storage.admin`)
- ✅ Firewall 8000 gắn `target-tags=mlops-serve`, không mở toàn project
- ✅ Hỏi lại trước khi: tạo VM, xóa VM, force-push, hoặc bất kỳ thao tác không đảo ngược nào
- ✅ Mọi commit đều đi qua nhánh/PR nếu bạn muốn review trước khi vào `main`
