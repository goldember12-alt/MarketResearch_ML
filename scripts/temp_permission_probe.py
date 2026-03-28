"""Probe temp-directory and write-permission behavior on Windows."""

from __future__ import annotations

import os
import shutil
import tempfile
import traceback
from pathlib import Path


def print_header(title: str) -> None:
    print(f"\n## {title}")


def show_env() -> None:
    print_header("Environment")
    for key in ("TEMP", "TMP", "USERPROFILE", "LOCALAPPDATA"):
        print(f"{key}={os.environ.get(key)}")
    print(f"gettempdir={tempfile.gettempdir()}")


def write_probe(path: Path, label: str) -> None:
    print_header(f"Write Probe: {label}")
    print(f"path={path}")
    print(f"exists={path.exists()}")
    if not path.exists():
        print("status=missing")
        return
    probe_dir = path / f"codex_probe_{label.replace(' ', '_').replace('%', '')}"
    try:
        probe_dir.mkdir(parents=True, exist_ok=True)
        probe_file = probe_dir / "probe.txt"
        probe_file.write_text("ok", encoding="utf-8")
        print(f"status=write_ok content={probe_file.read_text(encoding='utf-8')!r}")
    except Exception as exc:  # noqa: BLE001
        print(f"status=write_fail exception={type(exc).__name__}: {exc}")
        print(traceback.format_exc())
    finally:
        try:
            if probe_dir.exists():
                shutil.rmtree(probe_dir)
        except Exception as exc:  # noqa: BLE001
            print(f"cleanup_exception={type(exc).__name__}: {exc}")
            print(traceback.format_exc())


def tempfile_probe(repo_root: Path) -> None:
    print_header("tempfile.mkdtemp")
    temp_dir_path: Path | None = None
    try:
        temp_dir_path = Path(tempfile.mkdtemp())
        print(f"mkdtemp_path={temp_dir_path}")
        temp_file = temp_dir_path / "temp_probe.txt"
        temp_file.write_text("ok", encoding="utf-8")
        print(f"mkdtemp_write_ok content={temp_file.read_text(encoding='utf-8')!r}")
    except Exception as exc:  # noqa: BLE001
        print(f"mkdtemp_exception={type(exc).__name__}: {exc}")
        print(traceback.format_exc())
    finally:
        if temp_dir_path is not None:
            try:
                shutil.rmtree(temp_dir_path)
            except Exception as exc:  # noqa: BLE001
                print(f"mkdtemp_cleanup_exception={type(exc).__name__}: {exc}")
                print(traceback.format_exc())

    print_header("TemporaryDirectory")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            print(f"temporarydirectory_path={tmp_path}")
            temp_file = tmp_path / "tempdir_probe.txt"
            temp_file.write_text("ok", encoding="utf-8")
            print(
                "temporarydirectory_write_ok "
                f"content={temp_file.read_text(encoding='utf-8')!r}"
            )
    except Exception as exc:  # noqa: BLE001
        print(f"temporarydirectory_exception={type(exc).__name__}: {exc}")
        print(traceback.format_exc())

    print_header("Repo Root Write")
    try:
        probe_file = repo_root / "repo_root_probe.txt"
        probe_file.write_text("ok", encoding="utf-8")
        print(f"repo_write_ok content={probe_file.read_text(encoding='utf-8')!r}")
        probe_file.unlink()
    except Exception as exc:  # noqa: BLE001
        print(f"repo_write_exception={type(exc).__name__}: {exc}")
        print(traceback.format_exc())


def main() -> None:
    repo_root = Path.cwd()
    print(f"repo_root={repo_root}")
    print(f"under_onedrive={'OneDrive' in str(repo_root)}")
    show_env()

    temp = os.environ.get("TEMP")
    tmp = os.environ.get("TMP")
    local_temp = str(Path(os.environ["LOCALAPPDATA"]) / "Temp") if os.environ.get("LOCALAPPDATA") else None
    path_specs = [
        ("repo_root", repo_root),
        ("TEMP", Path(temp) if temp else None),
        ("TMP", Path(tmp) if tmp else None),
        ("LOCALAPPDATA_Temp", Path(local_temp) if local_temp else None),
        ("C_temp", Path("C:/temp")),
    ]
    for label, path in path_specs:
        if path is None:
            print_header(f"Write Probe: {label}")
            print("path=<unset>")
            print("status=missing")
            continue
        write_probe(path, label)

    tempfile_probe(repo_root)


if __name__ == "__main__":
    main()
