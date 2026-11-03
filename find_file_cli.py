import argparse
import os
from pathlib import Path
import shutil
import sys


def normalize_extension(ext: str) -> str:
    """ensure the file extension starts with a dot and is lowercase"""
    ext = ext.strip().lower()
    if not ext.startswith("."):
        ext = f".{ext}"
    return ext


def find_files(
    extension: str,
    directory: Path,
    recursive: bool = True,
    exclude_dir: Path | None = None,
) -> list[Path]:
    """find all files matching the extension (case-insensitive) in the directory"""
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    if not directory.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    ext = normalize_extension(extension)
    resolved_exclude = exclude_dir.resolve() if exclude_dir else None

    matched_files: list[Path] = []
    if recursive:
        for root, dirs, files in os.walk(directory):
            root_path = Path(root).resolve()
            if resolved_exclude:
                # prevent descending into the output directory if it is inside the search directory
                dirs[:] = [
                    d for d in dirs if (root_path / d).resolve() != resolved_exclude
                ]
                if root_path == resolved_exclude:
                    continue

            for file in files:
                if file.lower().endswith(ext):
                    matched_files.append(Path(root) / file)
    else:
        for item in directory.iterdir():
            if item.is_file() and item.name.lower().endswith(ext):
                matched_files.append(item)

    return sorted(matched_files)


def get_unique_destination(dest_dir: Path, filename: str) -> Path:
    """return a non-colliding file path inside dest_dir"""
    candidate = dest_dir / filename
    if not candidate.exists():
        return candidate

    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1
    while True:
        candidate = dest_dir / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def copy_files(files: list[Path], output_dir: Path) -> int:
    """copy all found files into output_dir, avoiding filename collisions"""
    output_dir.mkdir(parents=True, exist_ok=True)
    resolved_output = output_dir.resolve()
    copied_count = 0

    for file_path in files:
        if file_path.parent.resolve() == resolved_output:
            continue
        dest_path = get_unique_destination(output_dir, file_path.name)
        shutil.copy2(file_path, dest_path)
        copied_count += 1

    return copied_count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find all files of a specified type in a directory."
    )
    parser.add_argument(
        "file_type",
        help="File extension to search for (e.g., .gif, .txt, gif, txt).",
    )
    parser.add_argument(
        "directory",
        type=Path,
        help="Path to the directory to search.",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Only search the top-level directory without subdirectories.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Destination directory to copy all found files into.",
    )

    args = parser.parse_args()
    ext = normalize_extension(args.file_type)

    try:
        matches = find_files(
            ext,
            args.directory.resolve(),
            recursive=not args.no_recursive,
            exclude_dir=args.output,
        )
    except (FileNotFoundError, NotADirectoryError, PermissionError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    for match in matches:
        print(match)

    print(f"\nFound {len(matches)} {ext} file(s).")

    if args.output and matches:
        try:
            copied = copy_files(matches, args.output)
            print(f"Copied {copied} {ext} file(s) to '{args.output.resolve()}'.")
        except OSError as exc:
            print(f"Error copying files: {exc}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
