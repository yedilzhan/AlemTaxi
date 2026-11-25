"""Функциональный аудит конфигурации: сверка таблицы трассировки с кодом.

Проверяет в обе стороны:
    1) требование -> тест: каждый тест из столбца «Тест» таблицы существует;
    2) код -> требование: каждое исключение слоя логики упомянуто в таблице.

Запуск из папки проверяемого проекта:
    python ../taxi/tools/trace_check.py docs/lab7-report.md drivers/services.py rides/services.py
"""

import ast
import pathlib
import re
import sys


def trace_table(md_path):
    """Строки таблицы, у которой последний столбец называется «Тест»; иначе None."""
    blocks, block = [], []
    for line in pathlib.Path(md_path).read_text(encoding="utf-8").splitlines():
        if line.startswith("|"):
            block.append(line)
        elif block:
            blocks.append(block)
            block = []
    if block:
        blocks.append(block)
    for rows in blocks:
        cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
        if cells[0][-1].lower() == "тест":
            return [c for c in cells[1:] if not re.fullmatch(r"[\s\-:|]+", "".join(c))]
    return None


def test_names(root="."):
    """Имена всех функций test* во всех файлах test*.py проекта."""
    names = set()
    for path in pathlib.Path(root).rglob("test*.py"):
        if ".venv" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names |= {
            n.name
            for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name.startswith("test")
        }
    return names


def error_classes(path):
    """Классы исключений слоя логики (имена, оканчивающиеся на Error)."""
    tree = ast.parse(pathlib.Path(path).read_text(encoding="utf-8"))
    return [
        n.name
        for n in tree.body
        if isinstance(n, ast.ClassDef) and n.name.endswith("Error")
    ]


def main(table, *services):
    rows = trace_table(table)
    if rows is None:
        print(f"В {table} нет таблицы трассировки (столбец «Тест»): НС по пункту Б-1")
        return 1
    tests = test_names()
    text = "\n".join(" | ".join(r) for r in rows)
    problems = 0
    print(f"Строк в таблице трассировки: {len(rows)}; тестов в проекте: {len(tests)}")
    for row in rows:
        for name in re.findall(r"test_\w+", row[-1]):
            if name not in tests:
                problems += 1
                print(f"  НЕТ ТЕСТА     {row[0]!r}: {name}")
    for path in services:
        for cls in error_classes(path):
            if cls not in text:
                problems += 1
                print(f"  НЕТ В ТАБЛИЦЕ исключение {cls} из {path}")
    print("Итог:", "расхождений нет" if not problems else f"расхождений: {problems}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(*sys.argv[1:]))
