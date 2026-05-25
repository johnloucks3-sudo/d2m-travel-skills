from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from pathlib import Path
import markdown
import re
import yaml

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

BLOG_DIR = Path(__file__).parent.parent / "blog"


def _parse_post(path: Path) -> dict | None:
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception:
        return None

    frontmatter = {}
    body = raw
    if raw.startswith("---"):
        end = raw.find("\n---", 3)
        if end != -1:
            fm_text = raw[3:end].strip()
            try:
                frontmatter = yaml.safe_load(fm_text) or {}
            except Exception:
                pass
            body = raw[end + 4:].strip()

    if frontmatter.get("status", "published") != "published":
        return None

    # Strip the H1 title from body (we render it from frontmatter)
    body = re.sub(r"^#\s+.+\n", "", body, count=1)

    html_body = markdown.markdown(
        body,
        extensions=["extra", "toc", "nl2br"],
    )

    return {
        "slug": frontmatter.get("slug", path.stem),
        "title": frontmatter.get("title", path.stem),
        "byline": frontmatter.get("byline", ""),
        "date": str(frontmatter.get("date", "")),
        "tags": frontmatter.get("tags", []),
        "seo_title": frontmatter.get("seo_title", frontmatter.get("title", "")),
        "meta_description": frontmatter.get("meta_description", ""),
        "hero_image": frontmatter.get("hero_image", ""),
        "body_html": html_body,
        "reading_time": max(1, len(body.split()) // 200),
    }


def _all_posts() -> list[dict]:
    posts = []
    for path in sorted(BLOG_DIR.glob("*.md"), reverse=True):
        post = _parse_post(path)
        if post:
            posts.append(post)
    return posts


@router.get("/blog", response_class=HTMLResponse)
async def blog_index(request: Request):
    posts = _all_posts()
    return templates.TemplateResponse(
        "blog_list.html",
        {"request": request, "posts": posts},
    )


@router.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post(request: Request, slug: str):
    for path in BLOG_DIR.glob("*.md"):
        post = _parse_post(path)
        if post and post["slug"] == slug:
            return templates.TemplateResponse(
                "blog_post.html",
                {"request": request, "post": post},
            )
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Post not found")
