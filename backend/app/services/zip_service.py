"""Safely extracts a teacher-uploaded ZIP activity (HTML + CSS/JS/images)
with no manual deployment or hosting configuration required.

Handles the two real risks a ZIP upload introduces that a plain HTML upload
doesn't: path traversal (a crafted entry name trying to escape the archive)
and zip bombs (a tiny file that decompresses to something huge). Neither
concern applies to a single HTML file, which is why this is its own module
rather than folded into the existing upload handling.
"""

import io
import posixpath
import zipfile

MAX_TOTAL_UNCOMPRESSED = 20 * 1024 * 1024  # 20 MB
MAX_FILE_UNCOMPRESSED = 5 * 1024 * 1024  # 5 MB per file
MAX_FILE_COUNT = 300

_IGNORED_PREFIXES = ("__MACOSX/",)
_IGNORED_SUFFIXES = (".DS_Store",)


def _safe_relpath(name: str) -> str | None:
    if any(name.startswith(p) for p in _IGNORED_PREFIXES) or any(name.endswith(s) for s in _IGNORED_SUFFIXES):
        return None
    normalized = posixpath.normpath(name.replace("\\", "/"))
    if normalized in (".", "") or normalized.startswith("..") or normalized.startswith("/"):
        return None
    return normalized


def extract_zip_activity(raw_bytes: bytes) -> tuple[str, dict[str, bytes]]:
    """Returns (entry_html_text, {relative_path: raw_bytes}) for every other
    file in the archive. Raises ValueError with a teacher-readable message
    on anything that should reject the upload."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw_bytes))
    except zipfile.BadZipFile:
        raise ValueError("That file isn't a valid ZIP archive.")

    infos = [i for i in zf.infolist() if not i.is_dir()]
    if len(infos) > MAX_FILE_COUNT:
        raise ValueError(f"ZIP contains too many files (limit {MAX_FILE_COUNT}).")

    total_size = 0
    files: dict[str, bytes] = {}
    for info in infos:
        rel = _safe_relpath(info.filename)
        if rel is None:
            continue
        if info.file_size > MAX_FILE_UNCOMPRESSED:
            raise ValueError(f"'{rel}' is too large once extracted (limit 5 MB per file).")
        total_size += info.file_size
        if total_size > MAX_TOTAL_UNCOMPRESSED:
            raise ValueError("This ZIP is too large once extracted (limit 20 MB total).")
        files[rel] = zf.read(info)

    html_candidates = [p for p in files if p.lower().endswith((".html", ".htm"))]
    if not html_candidates:
        raise ValueError("No HTML file found in the ZIP archive.")

    entry_path = next((p for p in html_candidates if posixpath.basename(p).lower() == "index.html"), None)
    if entry_path is None:
        entry_path = next((p for p in html_candidates if posixpath.basename(p).lower() == "index.htm"), None)
    if entry_path is None:
        # No index.html/.htm: fall back to the shallowest, then
        # alphabetically first HTML file, so the choice is deterministic.
        entry_path = sorted(html_candidates, key=lambda p: (p.count("/"), p))[0]

    entry_html = files.pop(entry_path).decode("utf-8", errors="replace")
    return entry_html, files
