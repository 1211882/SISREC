import json
import csv
from pathlib import Path
from collections import defaultdict

SOURCE_FILE = Path("data/user.json")
REVIEW_FILE = Path("data/review.json")
EXTRA_FILE = Path("data/person_10000.csv")
OUTPUT_FILE = Path("data/user_final.json")
TARGET_USERS = 300
MIN_REVIEWS = 5


def read_json_lines(file_path: Path):
    with file_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def read_csv_rows(file_path: Path):
    with file_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row


def build_review_user_ids(file_path: Path):
    ordered_ids = []
    seen = set()
    review_counts = defaultdict(int)

    for review in read_json_lines(file_path):
        user_id = review.get("user_id")
        if not user_id:
            continue

        review_counts[user_id] += 1
        if user_id not in seen:
            seen.add(user_id)
            ordered_ids.append(user_id)

    eligible_ordered_ids = [
        user_id for user_id in ordered_ids if review_counts[user_id] > MIN_REVIEWS
    ]
    limited_ids = eligible_ordered_ids[:TARGET_USERS]
    return limited_ids, set(limited_ids)


def build_final_dataset():
    if not REVIEW_FILE.exists():
        print("Erro: falta o ficheiro data/review.json")
        print("Corre primeiro: python -m app.scripts.build_final_review")
        return

    print("A ler user_ids a partir de review.json...")
    ordered_user_ids, target_user_ids = build_review_user_ids(REVIEW_FILE)

    if not target_user_ids:
        print("Nenhum user_id encontrado nas reviews selecionadas.")
        return

    print(f"Users alvo (> {MIN_REVIEWS} reviews, máx {TARGET_USERS}): {len(target_user_ids)}")
    print("A ler ficheiro CSV extra...")
    extra_records = list(read_csv_rows(EXTRA_FILE))
    print(f"Registos CSV lidos: {len(extra_records)}")

    print("A selecionar users correspondentes por user_id...")
    selected_by_id = {}
    for index, record in enumerate(read_json_lines(SOURCE_FILE)):
        user_id = record.get("user_id")
        if user_id not in target_user_ids or user_id in selected_by_id:
            continue

        extra = extra_records[index] if index < len(extra_records) else {}

        first_name = (extra.get("firstname") or "").strip()
        last_name = (extra.get("lastname") or "").strip()
        full_name = f"{first_name} {last_name}".strip()
        if full_name:
            record["name"] = full_name

        age_raw = extra.get("age")
        if age_raw in (None, ""):
            record["age"] = None
        else:
            try:
                record["age"] = int(age_raw)
            except ValueError:
                record["age"] = age_raw

        record["gender"] = extra.get("gender")
        selected_by_id[user_id] = record

        if len(selected_by_id) == len(target_user_ids):
            break

    final_records = [selected_by_id[user_id] for user_id in ordered_user_ids if user_id in selected_by_id]

    print(f"Registos selecionados: {len(final_records)}")

    print("A gravar ficheiro final...")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.touch(exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        for record in final_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"✔ Ficheiro criado com sucesso: {OUTPUT_FILE}")
    print(f"✔ Total final: {len(final_records)} registos")


if __name__ == "__main__":
    build_final_dataset()