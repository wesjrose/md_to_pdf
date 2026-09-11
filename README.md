# Markdown to PDF

Converts Markdown files in a folder to PDF. A PDF is created only when there is no matching PDF, or the Markdown file is newer than the existing PDF. Unchanged files are skipped. Bind `run.bat` to a Logitech G915 key so one press runs the converter.

Each run appends to `convert.log` in this program directory: processed files, skipped files, and failures.

## Setup (once)

1. Install [Python 3.10+](https://www.python.org/downloads/) if it is not already installed. During setup, check **Add python.exe to PATH**.
2. Double-click `setup.bat`. That creates a virtual environment, installs dependencies, and downloads Chromium for PDF rendering.

## Configure

Edit `config.yaml`:

- `input_folder` — folder of Markdown files (default: `markdown`)
- `output_folder` — where PDFs are written (default: `pdfs`)
- `font.family` — font name used in the PDF (for example `Calibri`, `Georgia`, `Segoe UI`)
- `font.file` — optional path to a `.ttf`, `.otf`, or `.woff2` file if you want a custom/embedded font
- `font.heading_family` / `font.heading_file` — optional heading font
- `page.format` — `Letter`, `A4`, or `Legal`
- `page.margin` — CSS margin, for example `0.75in`

You can also pass overrides on the command line:

```bat
run.bat --input "D:\resumes" --output "D:\resumes\pdfs" --font-family "Georgia"
run.bat --font-file "C:\Windows\Fonts\georgia.ttf"
```

## Bind a G915 key in Logitech G HUB

G-keys on the G915 are handled by G HUB, so the reliable approach is **Launch Application**, not a global Python hotkey.

1. Open **Logitech G HUB**.
2. Select the **G915**.
3. Open **Assignments** (or the key-slot view).
4. Click the G-key you want (for example **G5**).
5. Choose **SYSTEM** → **Launch Application**.
6. Browse to `run.bat` in this project folder.
7. Save. Press that G-key to convert every Markdown file in `input_folder`.

If the console flashes and closes, conversion succeeded. If something fails, the window stays open with the error.

To use a regular key instead of a G-key, assign that key in G HUB to the same **Launch Application** action, or create a G HUB macro that launches `run.bat`.

## Run without G HUB

Double-click `run.bat`, or from a terminal in this folder:

```bat
.venv\Scripts\python convert.py
```
