"""Convert every Markdown file in a folder to PDF."""

from __future__ import annotations

import argparse
import html
import logging
import sys
from pathlib import Path

import markdown
import yaml
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = ROOT / "config.yaml"
LOG_PATH = ROOT / "convert.log"


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("resume_converter")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter("%(message)s"))

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def load_config(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Config not found: {path}")
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data


def resolve_path(base: Path, value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = (base / path).resolve()
    return path


def file_url(path: Path) -> str:
    return path.resolve().as_uri()


def font_face(family: str, font_file: str, base: Path) -> str:
    if not font_file:
        return ""
    url = file_url(resolve_path(base, font_file))
    suffix = Path(font_file).suffix.lower()
    formats = {
        ".ttf": "truetype",
        ".otf": "opentype",
        ".woff": "woff",
        ".woff2": "woff2",
    }
    fmt = formats.get(suffix, "truetype")
    return (
        f"@font-face {{ font-family: '{family}'; src: url('{url}') format('{fmt}'); "
        "font-weight: 100 900; font-style: normal; }"
    )


def build_css(config: dict, config_dir: Path) -> str:
    font = config.get("font") or {}
    page = config.get("page") or {}
    family = font.get("family") or "Calibri"
    heading_family = font.get("heading_family") or family
    code_family = font.get("code_family") or "Consolas"
    size = font.get("size_pt") or 11
    margin = page.get("margin") or "0.75in"

    faces = [
        font_face(family, font.get("file") or "", config_dir),
        font_face(heading_family, font.get("heading_file") or "", config_dir),
        font_face(code_family, font.get("code_file") or "", config_dir),
    ]
    faces_css = "\n".join(face for face in faces if face)

    return f"""
    {faces_css}
    @page {{
      margin: {margin};
    }}
    html, body {{
      font-family: '{family}', Calibri, "Segoe UI", sans-serif;
      font-size: {size}pt;
      line-height: 1.45;
      color: #111;
    }}
    h1, h2, h3, h4, h5, h6 {{
      font-family: '{heading_family}', '{family}', Calibri, "Segoe UI", sans-serif;
      line-height: 1.25;
      margin: 1.1em 0 0.4em;
    }}
    h1 {{ font-size: 1.7em; margin-top: 0; }}
    h2 {{ font-size: 1.3em; border-bottom: 1px solid #ddd; padding-bottom: 0.15em; }}
    h3 {{ font-size: 1.12em; }}
    p {{ margin: 0.5em 0; }}
    ul, ol {{ margin: 0.4em 0 0.4em 1.2em; }}
    a {{ color: #0b57d0; }}
    code, pre {{
      font-family: '{code_family}', Consolas, "Courier New", monospace;
    }}
    code {{
      background: #f4f4f4;
      padding: 0.1em 0.3em;
      border-radius: 3px;
      font-size: 0.92em;
    }}
    pre {{
      background: #f4f4f4;
      padding: 0.8em 1em;
      overflow-x: auto;
      border-radius: 4px;
    }}
    pre code {{ background: none; padding: 0; }}
    blockquote {{
      margin: 0.8em 0;
      padding: 0.1em 0.9em;
      border-left: 4px solid #ccc;
      color: #444;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      margin: 0.8em 0;
    }}
    th, td {{
      border: 1px solid #ccc;
      padding: 0.35em 0.55em;
      text-align: left;
    }}
    th {{ background: #f6f6f6; }}
    img {{ max-width: 100%; }}
    """


def md_to_html(md_path: Path) -> str:
    text = md_path.read_text(encoding="utf-8")
    return markdown.markdown(
        text,
        extensions=["extra", "sane_lists", "smarty", "toc"],
    )


def wrap_html(body: str, css: str, title: str, md_dir: Path) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <base href="{file_url(md_dir)}/">
  <style>{css}</style>
</head>
<body>
{body}
</body>
</html>
"""


def collect_markdown(folder: Path, recursive: bool) -> list[Path]:
    pattern = "**/*.md" if recursive else "*.md"
    files = sorted(path for path in folder.glob(pattern) if path.is_file())
    return files


def pdf_destination(md_path: Path, input_folder: Path, output_folder: Path) -> Path:
    relative = md_path.relative_to(input_folder).with_suffix(".pdf")
    return output_folder / relative


def conversion_needed(md_path: Path, pdf_path: Path) -> tuple[bool, str]:
    if not pdf_path.is_file():
        return True, "no matching PDF"
    if md_path.stat().st_mtime > pdf_path.stat().st_mtime:
        return True, "markdown updated since PDF was created"
    return False, "PDF is up to date"


def write_pdf(page, md_path: Path, pdf_path: Path, css: str, page_format: str) -> None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    body = md_to_html(md_path)
    document = wrap_html(body, css, md_path.stem, md_path.parent)
    page.set_content(document, wait_until="networkidle")
    page.emulate_media(media="print")
    page.pdf(
        path=str(pdf_path),
        format=page_format,
        print_background=True,
        prefer_css_page_size=True,
    )


def convert_files(
    md_files: list[Path],
    input_folder: Path,
    output_folder: Path,
    css: str,
    page_format: str,
    logger: logging.Logger,
) -> int:
    processed = 0
    skipped = 0
    failed = 0
    pending: list[tuple[Path, Path, str]] = []

    logger.info("Scanning %s Markdown file(s) in %s", len(md_files), input_folder)
    for md_path in md_files:
        pdf_path = pdf_destination(md_path, input_folder, output_folder)
        needed, reason = conversion_needed(md_path, pdf_path)
        if not needed:
            skipped += 1
            logger.info("SKIPPED %s (%s)", md_path, reason)
            continue
        pending.append((md_path, pdf_path, reason))

    if not pending:
        logger.info(
            "Run complete. processed=%s skipped=%s failed=%s",
            processed,
            skipped,
            failed,
        )
        return 0

    output_folder.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        for md_path, pdf_path, reason in pending:
            try:
                write_pdf(page, md_path, pdf_path, css, page_format)
                processed += 1
                logger.info("PROCESSED %s -> %s (%s)", md_path, pdf_path, reason)
            except Exception as exc:  # noqa: BLE001 - report and continue
                failed += 1
                logger.error("FAILED %s (%s)", md_path, exc)
        browser.close()

    logger.info(
        "Run complete. processed=%s skipped=%s failed=%s",
        processed,
        skipped,
        failed,
    )
    return 1 if failed else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert all Markdown files in a folder to PDFs."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--input", type=Path, help="Override input folder")
    parser.add_argument("--output", type=Path, help="Override output folder")
    parser.add_argument("--font-file", help="Override body font file path")
    parser.add_argument("--font-family", help="Override body font family name")
    return parser.parse_args()


def main() -> int:
    logger = setup_logger()
    logger.info("----- conversion started -----")
    args = parse_args()
    try:
        config = load_config(args.config)
    except Exception as exc:  # noqa: BLE001
        logger.error("FAILED to load config %s (%s)", args.config, exc)
        return 1
    config_dir = args.config.resolve().parent

    if args.font_file:
        config.setdefault("font", {})["file"] = args.font_file
    if args.font_family:
        config.setdefault("font", {})["family"] = args.font_family

    input_folder = resolve_path(
        config_dir, args.input or config.get("input_folder") or "markdown"
    )
    output_folder = resolve_path(
        config_dir, args.output or config.get("output_folder") or "pdfs"
    )
    recursive = bool(config.get("recursive", True))
    page_format = (config.get("page") or {}).get("format") or "Letter"

    if not input_folder.is_dir():
        logger.error("FAILED input folder does not exist: %s", input_folder)
        return 1

    md_files = collect_markdown(input_folder, recursive)
    if not md_files:
        logger.info("No Markdown files found in %s", input_folder)
        logger.info("Run complete. processed=0 skipped=0 failed=0")
        return 0

    css = build_css(config, config_dir)
    logger.info("Output folder: %s", output_folder)
    return convert_files(
        md_files, input_folder, output_folder, css, page_format, logger
    )


if __name__ == "__main__":
    sys.exit(main())
