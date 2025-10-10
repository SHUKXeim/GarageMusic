import os

def collect_code(output_file="bot_code.txt"):
    with open(output_file, "w", encoding="utf-8") as out:
        for root, _, files in os.walk("."):
            for file in files:
                if file.endswith(".py"):
                    path = os.path.join(root, file)
                    out.write(f"\n\n# ===== {path} =====\n\n")
                    with open(path, "r", encoding="utf-8") as f:
                        out.write(f.read())
    print(f"✅ Код всех файлов сохранён в {output_file}")

if __name__ == "__main__":
    collect_code()
