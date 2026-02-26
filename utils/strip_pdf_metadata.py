#!/usr/bin/env python3
"""Remove document metadata from PDF files."""

import argparse
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Strip metadata (Info + XMP) from PDF files."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="One or more input PDF files.",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output PDF path (allowed only when a single input is provided).",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Rewrite each input file in place.",
    )
    parser.add_argument(
        "--password",
        help="Password for encrypted PDFs.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite output file(s) if they already exist.",
    )
    return parser.parse_args()


def resolve_output_path(
    input_path: Path,
    output_arg: str | None,
    in_place: bool,
    force: bool,
    multiple_inputs: bool,
) -> Path:
    if output_arg:
        if multiple_inputs:
            raise ValueError("--output can be used only with a single input.")
        if in_place:
            raise ValueError("Use either --output or --in-place, not both.")
        output_path = Path(output_arg).expanduser().resolve()
    elif in_place:
        output_path = input_path
    else:
        output_path = input_path.with_name(f"{input_path.stem}-stripped.pdf")

    if output_path.exists() and output_path != input_path and not force:
        raise FileExistsError(
            f"Output already exists: {output_path} (use --force to overwrite)."
        )

    return output_path


def strip_metadata(input_path: Path, output_path: Path, password: str | None) -> None:
    reader = PdfReader(str(input_path))
    if reader.is_encrypted:
        if not password:
            raise ValueError(f"Encrypted PDF requires --password: {input_path}")
        if reader.decrypt(password) == 0:
            raise ValueError(f"Failed to decrypt PDF with provided password: {input_path}")

    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    writer.xmp_metadata = None
    writer._info = None

    if output_path == input_path:
        tmp_path = input_path.with_name(f"{input_path.stem}.tmp.pdf")
        with tmp_path.open("wb") as f:
            writer.write(f)
        tmp_path.replace(input_path)
    else:
        with output_path.open("wb") as f:
            writer.write(f)


def main() -> int:
    args = parse_args()
    input_paths = [Path(p).expanduser().resolve() for p in args.inputs]

    for path in input_paths:
        if not path.exists():
            print(f"ERROR: File not found: {path}", file=sys.stderr)
            return 1
        if path.suffix.lower() != ".pdf":
            print(f"ERROR: Not a PDF file: {path}", file=sys.stderr)
            return 1

    try:
        for path in input_paths:
            out_path = resolve_output_path(
                input_path=path,
                output_arg=args.output,
                in_place=args.in_place,
                force=args.force,
                multiple_inputs=len(input_paths) > 1,
            )
            strip_metadata(path, out_path, args.password)
            print(f"Processed: {path} -> {out_path}")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
