"""Menu photo editor: take selected menu photos of a restaurant, optionally cut the dish out of its background (rembg,
isnet-general-use model, on this server; semi-transparent haze dropped and a soft shadow added), place it on a colour or uploaded background, add a logo, and return a zip."""

from __future__ import annotations

import io
import json
import re
import shutil
import tempfile
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
from django.http import HttpResponse
try:  # optional: without Pillow the rest of the site still runs and the editor says it isn't installed
    from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageStat
except ImportError:
    Image = ImageColor = ImageDraw = ImageFilter = ImageStat = None
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .api import _outlet
from .market_api import _market
from .models import MarketRestaurant

BATCH = 4  # photos per request; the page sends a whole menu as several batches into one job
JOBS = Path(tempfile.gettempdir()) / "codeonto-photo-jobs"
JOB_TTL = 2 * 3600
MAX_UPLOAD = 8 * 1024 * 1024
POSITIONS = {"tl", "tr", "bl", "br", "c"}
_session = None


def _rembg():
    """The background-removal model, loaded once per worker on first use (170 MB, downloaded once to ~/.u2net)."""
    global _session
    if _session is None:
        from rembg import new_session
        _session = new_session("isnet-general-use")
    return _session


def _safe(name: str) -> str:
    return re.sub(r"[^\w\- ]+", "", name or "").strip()[:80] or "item"


def _fetch(url: str) -> bytes | None:
    url = url.replace(",w_300/", ",w_1024/")  # Swiggy's CDN serves larger copies of the same photo
    try:
        r = httpx.get(url, timeout=20, follow_redirects=True)
        return r.content if r.status_code == 200 else None
    except httpx.HTTPError:
        return None


def _upload(request, key: str) -> Image.Image | None:
    f = request.FILES.get(key)
    if not f:
        return None
    if f.size > MAX_UPLOAD:
        raise ValueError(f"The {key.replace('_', ' ')} is over 8 MB.")
    try:
        return Image.open(f).convert("RGBA")
    except Exception as e:
        raise ValueError(f"The {key.replace('_', ' ')} isn't an image.") from e


def _cover(img: Image.Image, w: int, h: int) -> Image.Image:
    """img scaled and centre-cropped to fill w x h."""
    s = max(w / img.width, h / img.height)
    img = img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)
    left, top = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((left, top, left + w, top + h))


def _background(bg: Image.Image | None, opts: dict, size: int) -> Image.Image:
    return _cover(bg, size, size) if bg is not None else Image.new("RGBA", (size, size), ImageColor.getrgb(opts["bg_color"]) + (255,))


def _match_light(dish: Image.Image, under: Image.Image) -> Image.Image:
    """Nudge the dish's brightness and colour cast toward the background it sits on (gently: food colours stay true)."""
    mask = dish.getchannel("A")
    d = ImageStat.Stat(dish.convert("RGB"), mask).mean
    b = ImageStat.Stat(under.convert("RGB")).mean
    gains = [min(1.15, max(0.85, ((bb + 1) / (dd + 1)) ** 0.3)) for dd, bb in zip(d, b)]
    rgb = [c.point(lambda v, g=g: min(255, round(v * g))) for c, g in zip(dish.convert("RGB").split(), gains)]
    return Image.merge("RGBA", (*rgb, mask))


def edit(data: bytes, opts: dict, bg: Image.Image | None, logo: Image.Image | None) -> tuple[bytes, str]:
    """One photo through the chosen steps. Returns (file bytes, extension)."""
    img = Image.open(io.BytesIO(data)).convert("RGBA")
    if opts["remove_bg"]:
        from rembg import remove
        img = remove(img, session=_rembg())
        # steam, smoke and soft shadows come out half see-through and show as grey smudges: drop them, keep edges smooth
        img.putalpha(img.getchannel("A").point(lambda v: 0 if v < 140 else 255 if v > 230 else v))
        box = img.getbbox()
        if box:
            img = img.crop(box)
    size = opts["size"] or max(img.width, img.height)
    if opts["remove_bg"]:
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        room = size * opts["dish_size"] / 100
        s = min(room / img.width, room / img.height)
        # table angle: a plate on a table seen from the side looks flatter than one shot from above
        w, h = max(1, round(img.width * s)), max(1, round(img.height * s * (1 - opts["tilt"] / 100)))
        dish = img.resize((w, h), Image.LANCZOS)
        x = min(max(0, round(size * opts["pos_x"] / 100 - w / 2)), size - w)
        y = min(max(0, round(size * opts["pos_y"] / 100 - h / 2)), size - h)
        if opts["match_light"] and (bg is not None or opts["bg_color"]):
            dish = _match_light(dish, _background(bg, opts, size).crop((x, y, x + w, y + h)))
        mask = dish.getchannel("A")
        # soft shadow cast down-right, then a tight dark contact shadow where the plate touches the surface
        shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        shadow.paste((0, 0, 0, 255), (x + size // 75, y + size // 33), mask.point(lambda v: 70 if v else 0))
        canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(size / 43)))
        contact = Image.new("L", canvas.size, 0)
        ImageDraw.Draw(contact).ellipse((x + w * 0.08, y + h * 0.86, x + w * 0.92, y + h * 1.02), fill=120)
        canvas.alpha_composite(Image.merge("RGBA", (*[Image.new("L", canvas.size, 0)] * 3, contact.filter(ImageFilter.GaussianBlur(size / 120)))))
        canvas.alpha_composite(dish, (x, y))
    else:
        canvas = _cover(img, size, size) if opts["size"] else img
    if bg is not None or opts["bg_color"]:
        base = _background(bg, opts, canvas.width) if canvas.width == canvas.height else (
            _cover(bg, canvas.width, canvas.height) if bg is not None else Image.new("RGBA", canvas.size, ImageColor.getrgb(opts["bg_color"]) + (255,)))
        base.alpha_composite(canvas)
        canvas = base
    if logo is not None:
        lw = max(1, round(canvas.width * opts["logo_size"] / 100))
        mark = logo.resize((lw, max(1, round(logo.height * lw / logo.width))), Image.LANCZOS)
        if opts["logo_opacity"] < 100:
            mark.putalpha(mark.getchannel("A").point(lambda a: a * opts["logo_opacity"] // 100))
        m = round(canvas.width * 0.04)
        x = {"tl": m, "bl": m, "tr": canvas.width - mark.width - m, "br": canvas.width - mark.width - m}.get(opts["logo_pos"], (canvas.width - mark.width) // 2)
        y = {"tl": m, "tr": m, "bl": canvas.height - mark.height - m, "br": canvas.height - mark.height - m}.get(opts["logo_pos"], (canvas.height - mark.height) // 2)
        canvas.alpha_composite(mark, (x, y))
    out = io.BytesIO()
    if canvas.getchannel("A").getextrema()[0] < 255:
        canvas.save(out, "PNG", optimize=True)
        return out.getvalue(), ".png"
    canvas.convert("RGB").save(out, "JPEG", quality=90)
    return out.getvalue(), ".jpg"


def _options(p) -> dict:
    def num(key, default, lo, hi):
        try:
            return min(hi, max(lo, int(p.get(key) or default)))
        except ValueError:
            return default
    color = (p.get("bg_color") or "").strip()
    if color and not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        raise ValueError("Background colour must look like #ffffff.")
    return {"remove_bg": p.get("remove_bg") in ("1", "true", "on"), "bg_color": color,
            "size": num("size", 1000, 0, 2000), "dish_size": num("dish_size", 84, 20, 100),
            "pos_x": num("pos_x", 50, 0, 100), "pos_y": num("pos_y", 50, 0, 100), "tilt": num("tilt", 0, 0, 50),
            "match_light": p.get("match_light") in ("1", "true", "on"),
            "logo_pos": p.get("logo_pos") if p.get("logo_pos") in POSITIONS else "br",
            "logo_size": num("logo_size", 20, 5, 60), "logo_opacity": num("logo_opacity", 100, 10, 100)}


def _job_dir(job: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{32}", job or ""):
        raise ValueError("Bad job id.")
    return JOBS / job


def _sweep():
    """Forget jobs nobody downloaded."""
    if JOBS.exists():
        for d in JOBS.iterdir():
            if time.time() - d.stat().st_mtime > JOB_TTL:
                shutil.rmtree(d, ignore_errors=True)


@api_view(["POST"])
def edit_photos(request, brand_id, outlet_id, platform, res_id):
    """One batch (up to BATCH photos) of an edit job. POST multipart: job (32 hex, from the page), item_ids (JSON list),
    remove_bg, bg_color, bg_image (file), logo (file), logo_pos, logo_size, logo_opacity, size (square px, 0 = keep),
    padding (% around a cut-out dish). Edited photos are kept under the job until GET .../images/edit/<job> zips them."""
    mk = _market(platform)
    _outlet(request, brand_id, outlet_id)
    if Image is None:
        return Response({"detail": "The photo editor isn't installed on this server yet."}, status=503)
    r = MarketRestaurant.objects.filter(platform=mk.code, res_id=res_id).first()
    try:
        folder = _job_dir(request.data.get("job"))
        ids = {str(i) for i in json.loads(request.data.get("item_ids") or "[]")}
        opts = _options(request.data)
        bg, logo = _upload(request, "bg_image"), _upload(request, "logo")
    except (ValueError, TypeError) as e:
        return Response({"detail": str(e)}, status=400)
    items = [i for i in (r.items if r else []) if i.get("image") and str(i["id"]) in ids]
    if not items:
        return Response({"detail": "Pick at least one item that has a photo."}, status=400)
    if len(items) > BATCH:
        return Response({"detail": f"Send up to {BATCH} photos per batch."}, status=400)
    if not (opts["remove_bg"] or opts["bg_color"] or bg or logo or opts["size"]):
        return Response({"detail": "Choose at least one change."}, status=400)

    _sweep()
    with ThreadPoolExecutor(max_workers=8) as pool:
        blobs = list(pool.map(_fetch, [i["image"] for i in items]))
    failed = []
    for i, data in zip(items, blobs):
        try:
            if not data:
                raise ValueError("download failed")
            content, ext = edit(data, opts, bg, logo)
        except Exception:
            failed.append(i.get("name", ""))
            continue
        cat = folder / _safe(i.get("category"))
        cat.mkdir(parents=True, exist_ok=True)
        name, n = _safe(i.get("name")), 2
        path = cat / f"{name}{ext}"
        while path.exists():
            path, n = cat / f"{name} ({n}){ext}", n + 1
        path.write_bytes(content)
    if failed:
        folder.mkdir(parents=True, exist_ok=True)
        with open(folder / "could-not-edit.txt", "a") as f:
            f.write("".join(n + "\n" for n in failed))
    return Response({"done": len(items) - len(failed), "failed": failed})


@api_view(["GET"])
def edit_photos_zip(request, brand_id, outlet_id, platform, res_id, job):
    """The finished job as one zip, one folder per category. The job is deleted once sent."""
    mk = _market(platform)
    _outlet(request, brand_id, outlet_id)
    try:
        folder = _job_dir(job)
    except ValueError as e:
        return Response({"detail": str(e)}, status=400)
    if not folder.exists():
        return Response({"detail": "Nothing to download: the edit expired or never ran. Edit the photos again."}, status=404)
    r = MarketRestaurant.objects.filter(platform=mk.code, res_id=res_id).first()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        for f in sorted(folder.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(folder).as_posix())
    shutil.rmtree(folder, ignore_errors=True)
    resp = HttpResponse(buf.getvalue(), content_type="application/zip")
    resp["Content-Disposition"] = f'attachment; filename="{mk.code}-{_safe(r.name if r else res_id).lower().replace(" ", "-")}-edited-photos.zip"'
    return resp
