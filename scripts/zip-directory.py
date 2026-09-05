"""Archive a plugin or a single Skill with its contents at the ZIP root."""
import pathlib
import sys
import zipfile


def archive(source: str, destination: str) -> None:
    root = pathlib.Path(source).resolve()
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as output:
        for entry in sorted(root.rglob("*")):
            if entry.is_symlink() and entry.is_dir():
                raise ValueError(f"Directory symlink cannot be packaged portably: {entry}")
            if not entry.resolve().is_relative_to(root):
                raise ValueError(f"Resource escapes archive root: {entry}")
            if entry.is_file():
                output.write(entry, entry.relative_to(root).as_posix())


if __name__ == "__main__":
    archive(*sys.argv[1:])
