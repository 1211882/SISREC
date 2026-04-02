import json
from pathlib import Path

SOURCE_FILE = Path("data/business.json")
REVIEW_FILE = Path("data/review_final.json")
OUTPUT_FILE = Path("data/business_final.json")


def read_json_lines(file_path: Path):
	with file_path.open("r", encoding="utf-8") as f:
		for line in f:
			line = line.strip()
			if line:
				yield json.loads(line)


def build_review_business_ids(file_path: Path):
	ordered_ids = []
	seen = set()
	for review in read_json_lines(file_path):
		business_id = review.get("business_id")
		if business_id and business_id not in seen:
			seen.add(business_id)
			ordered_ids.append(business_id)
	return ordered_ids, seen


def build_final_dataset():
	if not REVIEW_FILE.exists():
		print("Erro: falta o ficheiro data/review_final.json")
		print("Corre primeiro: python -m app.scripts.build_final_review")
		return

	print("A ler business_ids a partir de review_final.json...")
	ordered_business_ids, target_business_ids = build_review_business_ids(REVIEW_FILE)

	if not target_business_ids:
		print("Nenhum business_id encontrado nas reviews selecionadas.")
		return

	print(f"Businesses alvo encontrados nas reviews: {len(target_business_ids)}")
	print("A selecionar businesses correspondentes por business_id...")

	selected_by_id = {}
	for record in read_json_lines(SOURCE_FILE):
		business_id = record.get("business_id")
		if business_id not in target_business_ids or business_id in selected_by_id:
			continue

		selected_by_id[business_id] = record
		if len(selected_by_id) == len(target_business_ids):
			break

	selected_records = [selected_by_id[business_id] for business_id in ordered_business_ids if business_id in selected_by_id]

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
