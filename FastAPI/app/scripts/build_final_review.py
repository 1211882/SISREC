import json
from pathlib import Path

SOURCE_CANDIDATES = [
    Path("data/review.json"),
    Path("data/review_raw.json"),
]
BUSINESS_SOURCE_CANDIDATES = [
    Path("data/business.json"),
    Path("data/business_raw.json"),
]
OUTPUT_FILE = Path("data/review_final.json")

LIMIT = 10000


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


def find_business_source_file():
    for file_path in BUSINESS_SOURCE_CANDIDATES:
        if file_path.exists():
            return file_path
    return None


def load_open_business_ids(file_path: Path):
    open_ids = set()
    for business in read_json_lines(file_path):
        if business.get("is_open") == 1:
            business_id = business.get("business_id")
            if business_id:
                open_ids.add(business_id)
    return open_ids


def build_final_dataset():
    source_file = find_source_file()
    business_source_file = find_business_source_file()

    if source_file is None:
        print("Erro: não foi encontrado nenhum ficheiro de origem de reviews.")
        print("Coloca um destes ficheiros em data/: review.json ou review_raw.json")
        return

    if business_source_file is None:
        print("Erro: não foi encontrado nenhum ficheiro de origem de businesses.")
        print("Coloca um destes ficheiros em data/: business.json ou business_raw.json")
        return

    print(f"Ficheiro de businesses: {business_source_file}")
    open_business_ids = load_open_business_ids(business_source_file)
    print(f"Businesses com is_open = 1: {len(open_business_ids)}")

    print(f"Ficheiro de origem: {source_file}")
    print(f"A selecionar os primeiros {LIMIT} reviews de businesses abertos...")

    selected_records = []
    for record in read_json_lines(source_file):
        business_id = record.get("business_id")
        if business_id not in open_business_ids:
            continue

        selected_records.append(record)
        if len(selected_records) == LIMIT:
            break

    print(f"Registos selecionados: {len(selected_records)}")
    print("A gravar ficheiro final...")

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        for record in selected_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Ficheiro criado com sucesso: {OUTPUT_FILE}")
    print(f"Total final: {len(selected_records)} registos")


if __name__ == "__main__":
    build_final_dataset()
