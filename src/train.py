import mlflow
import mlflow.sklearn
import pandas as pd
import yaml
import json
import joblib
import os
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, f1_score, classification_report, confusion_matrix

EVAL_THRESHOLD = 0.70

CLASS_LABELS = {0: "thap", 1: "trung_binh", 2: "cao"}

# Bonus 2: dang thuat toan. random_forest/gradient_boosting dung chung cac
# tham so n_estimators/max_depth/min_samples_split nen chi can factory don gian;
# logistic_regression can StandardScaler nen duoc boc trong Pipeline rieng.
_ENSEMBLE_FACTORY = {
    "random_forest": RandomForestClassifier,
    "gradient_boosting": GradientBoostingClassifier,
}


def build_model(model_type: str, model_params: dict):
    if model_type == "logistic_regression":
        return Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, random_state=42)),
        ])
    model_cls = _ENSEMBLE_FACTORY.get(model_type)
    if model_cls is None:
        raise ValueError(f"model_type khong duoc ho tro: {model_type}")
    return model_cls(**model_params, random_state=42)


def train(
    params: dict,
    data_path: str = "data/train_phase1.csv",
    eval_path: str = "data/eval.csv",
) -> float:
    """
    Huan luyen mo hinh va ghi nhan ket qua vao MLflow.

    Tham so:
        params     : dict chua cac sieu tham so cho model.
        data_path  : duong dan den file du lieu huan luyen.
        eval_path  : duong dan den file du lieu danh gia.

    Tra ve:
        accuracy (float): do chinh xac tren tap danh gia.
    """

    # TODO 1: Doc du lieu huan luyen va danh gia
    df_train = pd.read_csv(data_path)
    df_eval = pd.read_csv(eval_path)

    # TODO 2: Tach dac trung (X) va nhan (y)
    X_train = df_train.drop(columns=["target"])
    y_train = df_train["target"]
    X_eval = df_eval.drop(columns=["target"])
    y_eval = df_eval["target"]

    # Bonus 5: canh bao drift - lop nao chiem duoi 10% tap train thi in WARNING ro rang.
    label_distribution = (
        y_train.value_counts(normalize=True).sort_index().to_dict()
    )
    label_distribution = {str(k): float(v) for k, v in label_distribution.items()}
    for label, ratio in label_distribution.items():
        if ratio < 0.10:
            print(
                f"WARNING: lop '{label}' chi chiem {ratio:.2%} du lieu huan luyen "
                f"(< 10%) - co the anh huong chat luong mo hinh (data drift)."
            )

    # Bonus 2: model_type duoc rut ra tu ban sao cua params, khong sua params goc
    # (params goc con duoc dung de mlflow.log_params ghi nhan day du sieu tham so,
    # bao gom ca model_type, phuc vu so sanh cac thi nghiem tren MLflow UI).
    model_params = dict(params)
    model_type = model_params.pop("model_type", "random_forest")

    with mlflow.start_run(run_name=model_type):

        # TODO 3: Ghi nhan cac sieu tham so
        mlflow.log_params(params)
        mlflow.set_tag("model_type", model_type)

        # TODO 4: Khoi tao va huan luyen mo hinh
        # Goi y: su dung random_state=42 de dam bao tinh tai tao
        model = build_model(model_type, model_params)
        model.fit(X_train, y_train)

        # TODO 5: Du doan tren tap danh gia va tinh chi so
        preds = model.predict(X_eval)
        acc = accuracy_score(y_eval, preds)
        f1 = f1_score(y_eval, preds, average="weighted")

        # Bonus 3: bao cao tu dong - classification_report + confusion_matrix dang text
        report_dict = classification_report(
            y_eval, preds, target_names=[CLASS_LABELS[c] for c in sorted(CLASS_LABELS)],
            output_dict=True, zero_division=0,
        )
        report_text = classification_report(
            y_eval, preds, target_names=[CLASS_LABELS[c] for c in sorted(CLASS_LABELS)],
            zero_division=0,
        )
        cm = confusion_matrix(y_eval, preds)
        cm_text = "\n".join(" ".join(str(x) for x in row) for row in cm)

        os.makedirs("outputs", exist_ok=True)
        with open("outputs/report.txt", "w") as f:
            f.write("=== Classification Report ===\n")
            f.write(report_text)
            f.write("\n\n=== Confusion Matrix (hang=thuc te, cot=du doan) ===\n")
            f.write(cm_text)
            f.write("\n")
        mlflow.log_artifact("outputs/report.txt")

        # TODO 6: Ghi nhan chi so vao MLflow
        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("f1_score", f1)
        mlflow.sklearn.log_model(model, "model")

        # TODO 7: In ket qua ra man hinh
        print(f"Accuracy: {acc:.4f} | F1: {f1:.4f}")

        # TODO 8: Luu metrics ra file outputs/metrics.json
        # File nay duoc doc boi GitHub Actions o Buoc 2
        with open("outputs/metrics.json", "w") as f:
            json.dump(
                {
                    "accuracy": float(acc),
                    "f1_score": float(f1),
                    "model_type": model_type,
                    "label_distribution": label_distribution,
                    "classification_report": report_dict,
                },
                f,
                indent=2,
            )

        # TODO 9: Luu mo hinh ra file models/model.pkl
        # File nay duoc upload len GCS o Buoc 2
        os.makedirs("models", exist_ok=True)
        joblib.dump(model, "models/model.pkl")

    # TODO 10: Tra ve acc
    return float(acc)


if __name__ == "__main__":
    with open("params.yaml") as f:
        params = yaml.safe_load(f)
    train(params)
