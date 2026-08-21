Thực hiện TOÀN BỘ lab MLOps trong repo này — cả 3 bước chính lẫn 5 bonus, mục tiêu 100/100 điểm.

ĐỌC TRƯỚC KHI LÀM BẤT CỨ GÌ: `docs/PLAN.md` — kế hoạch chi tiết đã duyệt (9 giai đoạn, 35 TODO cần điền, 9 rủi ro kỹ thuật R1–R9, ma trận rubric→bằng chứng). Bám sát plan đó, đừng lập kế hoạch mới.

═══════════════════════════════════════════
GĐ -1: KIỂM TRA MÔI TRƯỜNG (LÀM ĐẦU TIÊN)
═══════════════════════════════════════════
Chạy đúng khối này TRƯỚC, rồi đối chiếu kết quả với bảng bên dưới:

```bash
python3 --version; git remote -v
gcloud auth list 2>&1 | head -5; gcloud config get-value project
gh auth status 2>&1 | head -5
ls -la sa-key.json .dvc/config ~/.ssh/mlops_deploy 2>&1
gsutil ls -p kis-check-aic 2>&1 | head
```

TRẠNG THÁI KỲ VỌNG (máy gốc của tôi — MacBook, /Users/nhatnguyen/Desktop/AIA/labs/...):
- gcloud: authed `nhatjames24.2004@gmail.com`, project `kis-check-aic`, role `roles/owner`, **billing đã bật** (`01C13D-9350D9-5A4025`)
- gh: authed `NhtJm`, scope `repo` + `workflow`
- Python 3.11.9 · repo `NhtJm/TRACK2-DAY21-2A202601155-TRANNGUYENTHENHAT` (PUBLIC, branch main)
- Compute Engine API **CHƯA bật** → cần `gcloud services enable compute.googleapis.com`
- Chưa có `.venv`, chưa cài dvc/mlflow

NẾU KHỚP → bỏ qua phần dưới, nhảy thẳng vào GĐ 0 của PLAN.md.

NẾU KHÁC (máy khác / môi trường mới) → xử lý theo bảng này:

| Triệu chứng | Cách khắc phục |
|---|---|
| `gcloud auth list` trống | Báo tôi chạy: `gcloud auth login` **và** `gcloud auth application-default login` (cần trình duyệt — tôi phải tự chạy, bạn không chạy hộ được). Sau đó `gcloud config set project kis-check-aic` |
| `gh auth status` lỗi | Báo tôi chạy `gh auth login` (chọn HTTPS, scope phải có `repo` + `workflow`) |
| **`sa-key.json` không tồn tại** | ⚠️ BẪY PHỔ BIẾN — file này bị `.gitignore` nên KHÔNG đi theo repo. Nếu SA `mlops-lab-sa` đã tồn tại thì tạo key mới: `gcloud iam service-accounts keys create sa-key.json --iam-account mlops-lab-sa@kis-check-aic.iam.gserviceaccount.com`. Nếu SA chưa có thì làm lại GĐ 3 của PLAN.md |
| `.dvc/config` đã có nhưng `dvc pull` fail | Do thiếu `sa-key.json` ở trên. Sau khi có key: `export GOOGLE_APPLICATION_CREDENTIALS=$PWD/sa-key.json` rồi thử lại |
| `~/.ssh/mlops_deploy` không có | Tạo mới `ssh-keygen -t ed25519 -f ~/.ssh/mlops_deploy -N ""`, add pubkey vào `authorized_keys` của VM, rồi CẬP NHẬT LẠI secret `VM_SSH_KEY` |
| `gsutil ls` không thấy bucket lab | Hạ tầng chưa dựng → chạy từ GĐ 3 |
| Thấy bucket + VM đã tồn tại | Hạ tầng đã có → **đừng tạo lại**, kiểm tra `gh secret list` và `gcloud compute instances list` rồi tiếp tục từ giai đoạn dang dở |
| Python không phải 3.10/3.11 | `requirements.txt` pin sklearn 1.4.2 (hỗ trợ 3.9–3.12). Nếu ngoài khoảng đó, báo tôi |

Nguyên tắc: **hạ tầng cloud (bucket / VM / IAM / GitHub Secrets) nằm trên cloud nên không mất khi đổi máy** — chỉ có credential local (gcloud token, gh token, sa-key.json, ssh key) là phải dựng lại. Luôn kiểm tra trước khi tạo mới để tránh tạo trùng bucket/VM.

═══════════════════════════════════════════
QUYẾT ĐỊNH ĐÃ CHỐT
═══════════════════════════════════════════
1. Cloud provider = **GCP**, project `kis-check-aic` (requirements.txt đã pin `dvc[gs]` + `google-cloud-storage`)
2. **Được phép tạo GCE VM** `e2-small` us-central1-a (chi phí < $0.15). Bật Compute API nếu cần.
3. Bonus 1 = **DagsHub** — tôi sẽ tự đăng ký tài khoản tại dagshub.com (login bằng GitHub NhtJm) và đưa bạn token. Khi đến GĐ 8 mà tôi chưa đưa token thì NHẮC tôi, đừng tự đăng ký hộ và đừng bỏ qua bonus này.

═══════════════════════════════════════════
YÊU CẦU BÀN GIAO (bắt buộc đủ 3 thứ)
═══════════════════════════════════════════
1. **Run logs đầy đủ** — mọi lệnh ghi vào `docs/logs/*.log` theo đúng cấu trúc §2 của PLAN.md. Không tóm tắt, giữ nguyên stdout/stderr thật.
2. **Output lệnh đầy đủ** — `docs/evidence/` chứa `mlflow-runs.csv`, `metrics-step2.json`, `metrics-step3.json`, `report.txt`.
3. **`docs/report.html`** — trang HTML tự chứa (inline CSS/JS, không CDN), theme-aware, gồm: sơ đồ kiến trúc SVG, giải thích từng đoạn code + lý do thiết kế, bảng so sánh 5 thí nghiệm MLflow, log thật của từng CI job, bảng đối chiếu Bước 2 (2998 mẫu) vs Bước 3 (5996 mẫu), 5 bonus kèm bằng chứng, bảng tự chấm rubric 100đ, nhật ký sự cố. Publish thành Artifact và đưa tôi link.
   Cộng thêm `docs/BAO-CAO.md` ≤1 trang A4 theo yêu cầu nộp bài.

═══════════════════════════════════════════
LƯU Ý KỸ THUẬT SỐNG CÒN (chi tiết PLAN.md §1)
═══════════════════════════════════════════
- **R1**: `max_depth=5` mặc định chỉ cho ~0.57 accuracy → **eval gate 0.70 sẽ chặn deploy**, mất 28 điểm. Bước 1 phải grid-search thật, ưu tiên `max_depth: null` + `n_estimators: 200–300`. Nếu RF không qua 0.70, kích hoạt Bonus 2 (`gradient_boosting`) sớm làm phương án dự phòng.
- **R2**: Bonus 2 thêm `model_type` vào params.yaml sẽ làm vỡ `RandomForestClassifier(**params)` → pop trên bản copy của dict.
- **R5**: Bonus 5 không bao giờ cảnh báo với data thật (phân phối 37/44/20%) → cần run demo riêng trên tập lệch.
- **R6**: Demo eval-gate-fail chạy bằng `workflow_dispatch` trên nhánh `demo/eval-gate-fail` với input threshold=0.99, để lịch sử `main` giữ toàn xanh.
- **R7**: Bonus 4 phải ĐỌC metrics.json cũ từ GCS TRƯỚC khi ghi đè metrics mới.
- **R9**: VM phải cài `scikit-learn==1.4.2` (pin đúng version) nếu không `joblib.load` lỗi version mismatch.
- **Bước 3**: `dvc push` PHẢI trước `git push`, và chỉ commit file `.dvc` chứ không commit `.csv`.

═══════════════════════════════════════════
AN TOÀN
═══════════════════════════════════════════
- Tuyệt đối KHÔNG commit `sa-key.json`, private key, hay file CSV — kiểm tra `git status` trước mỗi commit.
- KHÔNG in secret ra log; scan & redact log trước khi đưa vào report.html.
- Service Account chỉ `objectAdmin` trên đúng 1 bucket (không `storage.admin`).
- HỎI TÔI trước khi: xóa VM, force-push, hoặc bất kỳ thao tác không đảo ngược nào.

═══════════════════════════════════════════
CÁCH LÀM VIỆC
═══════════════════════════════════════════
- Chạy tuần tự GĐ 0→9 của PLAN.md. Báo cáo tại mỗi mốc M1–M6.
- Việc chờ máy (pip install, CI run, tạo VM) chạy nền, tranh thủ soạn HTML song song.
- Dự kiến ~6h45' tổng (chỉ phần chính ~3h55'). Nếu vướng >2 lần ở cùng một chỗ thì DỪNG hỏi tôi thay vì thử mò.
- Commit theo conventional commits tiếng Việt, khớp style repo (xem `git log`).
- Khi cần tôi chạy lệnh tương tác (gcloud auth login, gh auth login), bảo tôi gõ `! <lệnh>` trong khung chat để output vào thẳng hội thoại.
