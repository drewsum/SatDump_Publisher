import argparse
import hashlib
import json
from pathlib import Path
import os
import shutil
from urllib.parse import quote
import time
from typing import List

from . import db as _db

try:
    from PIL import Image
except Exception:
    Image = None

try:
    from jinja2 import Environment, FileSystemLoader
except Exception:
    Environment = None
    FileSystemLoader = None


def find_images(root: Path, exts: List[str]) -> List[Path]:
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        for fn in filenames:
            if any(fn.lower().endswith(ext) for ext in exts):
                files.append(Path(dirpath) / fn)
    return files


def file_info(path: Path, base: Path, compute_hash: bool = True):
    stat = path.stat()
    rel = str(path.relative_to(base))
    info = {
        "path": rel,
        "size": stat.st_size,
        "mtime": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(stat.st_mtime)),
    }
    if compute_hash:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        info["sha256"] = h.hexdigest()
    return info


def extract_image_metadata(path: Path, base: Path, compute_hash: bool = True):
    stat = path.stat()
    rel = str(path.relative_to(base))
    size = stat.st_size
    # timestamp: try EXIF, else file mtime
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(stat.st_mtime))
    fmt = None
    width = None
    height = None
    if Image is not None:
        try:
            with Image.open(path) as im:
                fmt = im.format
                width, height = im.size
                exif = getattr(im, "_getexif", None)
                if exif:
                    dt = exif().get(36867) if callable(exif) else None
                    if dt:
                        timestamp = dt.replace(":", "-", 2)
        except Exception:
            pass
    sha = None
    if compute_hash:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        sha = h.hexdigest()
    return {
        "path": rel,
        "timestamp": timestamp,
        "format": fmt,
        "width": width,
        "height": height,
        "size": size,
        "sha256": sha,
    }


def create_image_map(root: Path, out_file: Path, exts: List[str], compute_hash: bool = True):
    root = root.resolve()
    files = find_images(root, exts)
    mapped = [file_info(p, root, compute_hash=compute_hash) for p in files]
    payload = {"root": str(root), "count": len(mapped), "images": mapped}
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(payload, indent=2))
    return payload


def main():
    parser = argparse.ArgumentParser(prog="satdump_publisher", description="SatDump Publisher - satdump tools")
    parser.add_argument("--path", default=None, help="Path to scan (default: /data if present, else current directory)")
    parser.add_argument("--no-hash", dest="no_hash", action="store_true", help="Do not compute SHA256 hashes")
    parser.add_argument("--output", dest="output_dir", default=None, help="Output dir for generated site (default: <path>/www)")
    parser.add_argument("--no-thumbs", dest="no_thumbs", action="store_true", help="Do not generate thumbnails")

    # allow unknown args (compose may add service name as an extra token)
    args, unknown = parser.parse_known_args()

    # scanning root vs writable data root
    data_root = Path("/data") if Path("/data").exists() else Path.cwd()
    scan_default = Path("/data/input") if Path("/data/input").exists() else data_root
    scan_root = Path(args.path) if args.path else scan_default
    root = scan_root
    exts = [".png", ".jpg", ".jpeg", ".gif"]

    # Always run: scan -> update DB in writable data_root -> generate site
    db_path = data_root / "db" / "satdump.db"
    conn = _db.ensure_db(db_path)
    files = find_images(root, exts)
    for p in files:
        meta = extract_image_metadata(p, root, compute_hash=not args.no_hash)
        _db.upsert_image(conn, path=meta["path"], timestamp=meta["timestamp"], format=meta["format"], width=meta["width"], height=meta["height"], size=meta["size"], sha256=meta["sha256"])
        print(f"Indexed: {meta['path']}")
    print(f"Indexed {len(files)} image(s) into {db_path}")

    # Generate site
    out = Path(args.output_dir) if args.output_dir else (data_root / "www")
    rows = _db.list_images(conn)
    images = []
    for r in rows:
        images.append({
            "path": r[0],
            "timestamp": r[1],
            "format": r[2],
            "width": r[3],
            "height": r[4],
            "size": r[5],
            "sha256": r[6],
        })
    out.mkdir(parents=True, exist_ok=True)
    # thumbnails
    if not args.no_thumbs:
        thumbs_dir = out / "thumbs"
        thumbs_dir.mkdir(exist_ok=True)
        if Image is None:
            print("Pillow not installed; cannot generate thumbnails")
        else:
            for idx, img in enumerate(images):
                src = root / img["path"]
                try:
                    with Image.open(src) as im:
                        im.thumbnail((320, 320))
                        im.convert("RGB").save(thumbs_dir / f"{idx}.jpg", format="JPEG")
                except Exception as e:
                    print(f"thumb error for {src}: {e}")

    # copy original images into site preserving relative paths so nginx can serve them
    images_dir = out / "images"
    # remove any stale copies to ensure sanitized set is authoritative
    if images_dir.exists():
        try:
            shutil.rmtree(images_dir)
        except Exception as e:
            print(f"warning: could not remove existing images dir: {e}")
    images_dir.mkdir(parents=True, exist_ok=True)
    for idx, img in enumerate(images):
        src = root / img["path"]
        try:
            rel = Path(img["path"])  # may include subdirs
            # sanitize each path segment to safe filename characters
            import re
            def _sanitize(segment: str) -> str:
                return re.sub(r'[^A-Za-z0-9._-]', '_', segment)

            sanitized_parts = [_sanitize(part) for part in rel.parts]
            dest_path = images_dir.joinpath(*sanitized_parts)
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            # copy file (overwrite if exists)
            shutil.copy2(src, dest_path)
            img["full"] = "images/" + "/".join(sanitized_parts)
        except Exception as e:
            print(f"copy error for {src}: {e}")

    # render template
    if Environment is None:
        print("Jinja2 not installed; cannot render site")
        return 1
    templates_path = Path(__file__).resolve().parent / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_path)))
    tpl = env.get_template("index.html")
    rendered = tpl.render(images=images)
    (out / "index.html").write_text(rendered, encoding="utf-8")
    # copy static assets
    static_src = templates_path / "static"
    static_dst = out / "static"
    if static_src.exists():
        for p in static_src.iterdir():
            content = p.read_bytes()
            (static_dst).mkdir(parents=True, exist_ok=True)
            (static_dst / p.name).write_bytes(content)
    print(f"Generated site at {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
