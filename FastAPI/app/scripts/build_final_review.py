import json
from pathlib import Path

SOURCE_CANDIDATES = [
    Path("data/review.json"),
    Path("data/review_raw.json"),
]
USER_FINAL_FILE = Path("data/user_final.json")
OUTPUT_FILE = Path("data/review_final.json")


def read_json_lines(file_path: Path):
    with file_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def find_source_file():
    for file_path in SOURCE_CANDIDATES:
        if file_path.exists():
            return file_path
    return None


def load_target_user_ids(user_file: Path):
    user_ids = []
    seen = set()
    for record in read_json_lines(user_file):
        user_id = record.get("user_id")
        if user_id and user_id not in seen:
            seen.add(user_id)
            user_ids.append(user_id)
    return user_ids, seen


def build_final_dataset():
    source_file = find_source_file()

    if source_file is None:
        print("Erro: não foi encontrado nenhum ficheiro de origem de reviews.")
        print("Coloca um destes ficheiros em data/: review.json ou review_raw.json")
        return

    if not USER_FINAL_FILE.exists():
        print("Erro: falta o ficheiro data/user_final.json")
        print("Corre primeiro: python -m app.scripts.build_final_user")
        return

    print(f"Ficheiro de origem: {source_file}")
    ordered_user_ids, selected_users_set = load_target_user_ids(USER_FINAL_FILE)
    print(f"Users carregados de user_final.json: {len(ordered_user_ids)}")
    print("A selecionar todas as reviews dos users em user_final.json (comparação por user_id)...")

    selected_records = []
    for record in read_json_lines(source_file):
        user_id = record.get("user_id")
        if user_id not in selected_users_set:
            continue

        selected_records.append(record)

    print(f"Registos selecionados: {len(selected_records)}")
    print("A gravar ficheiro final...")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.touch(exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        for record in selected_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Ficheiro criado com sucesso: {OUTPUT_FILE}")
    print(f"Total final: {len(selected_records)} registos")


if __name__ == "__main__":
    build_final_dataset()
