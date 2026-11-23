"""Сбор свидетельств аудита: вывод каждого инструмента сохраняется в UTF-8 файл.

Запуск из папки ПРОВЕРЯЕМОГО проекта, в его виртуальном окружении:
    python ../taxi/tools/collect_evidence.py ../taxi/docs/audit/evidence
"""

import datetime
import os
import pathlib
import re
import subprocess
import sys

OUT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "docs/audit/evidence")
PY = sys.executable
HERE = pathlib.Path(__file__).resolve().parent
APPS = ["config", "tariffs", "drivers", "rides"]  # каталоги с кодом проекта
EXCLUDE = "*/migrations/*,*\\migrations\\*,*/test*.py,*\\test*.py"
# Для чужого проекта поменяйте: таблица трассировки и файлы слоя логики
TRACE_ARGS = [
    "docs/lab7-report.md",
    "drivers/services.py",
    "rides/services.py",
    "tariffs/services.py",
]
CONVENTIONAL = re.compile(r"^(feat|fix|docs|test|refactor|chore|style)(\(.+\))?!?: ")
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}


def run(cmd):
    """Выполнить команду и вернуть её вывод (stdout + stderr) вместе с самой командой."""
    shown = " ".join(["python"] + cmd[1:]) if cmd[0] == PY else " ".join(cmd)
    try:
        p = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV
        )
        return f"$ {shown}\n{p.stdout}{p.stderr}\n"
    except FileNotFoundError as e:
        return f"$ {shown}\nне удалось запустить: {e}\n"


def git(*args):
    p = subprocess.run(
        ["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    return p.stdout


def save(name, text):
    (OUT / name).write_text(text, encoding="utf-8")
    print("записано", name)


def process_report():
    """Выборка процесса: последние 20 коммитов, авторы, лишние файлы."""
    subjects = [s for s in git("log", "-20", "--format=%s").splitlines() if s]
    good = [s for s in subjects if CONVENTIONAL.match(s)]
    share = 100 * len(good) // max(len(subjects), 1)
    text = f"Последние {len(subjects)} коммитов; по Conventional Commits: {len(good)} ({share} %)\n"
    text += "Не по правилам:\n" + "".join(f"  {s}\n" for s in subjects if s not in good)
    text += "\ngit shortlog -sn:\n" + git("shortlog", "-sn", "HEAD")
    extra = [
        f
        for f in git("ls-files").splitlines()
        if re.search(r"sqlite3|\.env|htmlcov|__pycache__|\.pyc$", f)
    ]
    text += "\nЛишние файлы в репозитории: " + (", ".join(extra) if extra else "нет") + "\n"
    return text


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    when = f"Дата сбора: {datetime.datetime.now():%Y-%m-%d %H:%M}\n"
    save(
        "00-commit.txt",
        run(["git", "rev-parse", "--short", "HEAD"])
        + run(["git", "log", "-1", "--format=%H %ci %s"])
        + when,
    )
    save("01-tests.txt", run([PY, "manage.py", "test"]))
    save("02-ruff.txt", run([PY, "-m", "ruff", "check", "."]))
    save(
        "03-radon.txt",
        run([PY, "-m", "radon", "cc", "-s", "-n", "B", *APPS, "manage.py"])
        + run([PY, "-m", "radon", "mi", "-s", *APPS, "manage.py"]),
    )
    save(
        "04-coverage.txt",
        run([PY, "-m", "coverage", "run", "--branch", "manage.py", "test"])
        + run([PY, "-m", "coverage", "report"]),
    )
    save("05-bandit.txt", run([PY, "-m", "bandit", "-r", *APPS, "-x", EXCLUDE]))
    save("06-pip-audit.txt", run([PY, "-m", "pip_audit", "-r", "requirements.txt"]))
    save("07-deploy.txt", run([PY, "manage.py", "check", "--deploy"]))
    save("08-trace.txt", run([PY, str(HERE / "trace_check.py"), *TRACE_ARGS]))
    save("09-freeze.txt", run([PY, "-m", "pip", "freeze"]))
    save("10-process.txt", process_report())


if __name__ == "__main__":
    main()
