#!/usr/bin/env python3
"""
Drive Intelligence Indexing — full-text/semantic search over Thunderbird Drive.

Indexes Thunderbird_Knowledge_Base + Thunderbird_Client_Files (all client
subfolders, recursive) into Qdrant collection `drive_fts` (separate from
`thunderbird_memories`). Each file becomes one or more chunks with metadata:
file_type, created_date, modified_date, owner, access_level, drive link.

Search combines a Qdrant full-text payload index (literal keyword match on
`content` + `name`) with vector similarity (FastEmbed, same local model as
core/memory/qdrant_memory.py — zero API cost) so a query like "Regent
pricing docs" ranks on both keyword presence and semantic similarity, and
can be narrowed with structured filters (file_type, date_range, owner).

CLI:
  python3 drive_fts_indexer.py index                 # full reindex
  python3 drive_fts_indexer.py index --folder <id>   # reindex one folder tree
  python3 drive_fts_indexer.py search "Regent pricing" --days 30
  python3 drive_fts_indexer.py search "excursion" --file-type pdf
"""

import argparse
import io
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastembed import TextEmbedding
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchText,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    Range,
    VectorParams,
)

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
DRIVE_TOKEN_FILE = THUNDERBIRD_DIR / "drive_token.json"
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]

COLLECTION = "drive_fts"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
VECTOR_SIZE = 384
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))

# Roots to index — Thunderbird_Knowledge_Base + Thunderbird_Client_Files (recursive).
# Source: docs/DRIVE_ARCHITECTURE.md
DEFAULT_ROOTS = {
    "Thunderbird_Knowledge_Base": "1MjjbqQVnzMYpHyAtNu-zZej-1mXhHkGk",
    "Thunderbird_Client_Files": "1l3WIjh2aL_fKEuDITmCIgQysfKVDNMUx",
}

CHUNK_WORDS = 300
OVERLAP_WORDS = 38
EMBED_BATCH = 80
MAX_FILE_CHARS = 100_000  # cap extracted text per file before chunking

GOOGLE_DOC_EXPORT = "text/plain"
GOOGLE_SHEET_EXPORT = "text/csv"
FOLDER_MIME = "application/vnd.google-apps.folder"

_NS = uuid.UUID("d2fb1a01-4c9e-4a5c-9e42-71a0b7f6c3e1")


def _point_id(file_id: str, chunk_index: int) -> str:
    return str(uuid.uuid5(_NS, f"{file_id}:{chunk_index}"))


def _chunk_text(text: str) -> list[str]:
    words = text.split()
    if len(words) <= CHUNK_WORDS:
        return [text] if text.strip() else []
    chunks = []
    start = 0
    while start < len(words):
        end = start + CHUNK_WORDS
        chunks.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        start = end - OVERLAP_WORDS
    return chunks


def _file_type_from_mime(mime_type: str) -> str:
    mapping = {
        "application/vnd.google-apps.document": "google_doc",
        "application/vnd.google-apps.spreadsheet": "google_sheet",
        "application/vnd.google-apps.presentation": "google_slides",
        "application/vnd.google-apps.folder": "folder",
        "application/pdf": "pdf",
        "text/plain": "text",
        "text/markdown": "markdown",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    }
    if mime_type in mapping:
        return mapping[mime_type]
    if mime_type.startswith("image/"):
        return "image"
    return "other"


def _access_level_from_permissions(permissions: list[dict] | None, owners: list[dict] | None) -> str:
    """Best-effort access-level label from Drive permission metadata."""
    if not permissions:
        return "private"
    roles = {p.get("role") for p in permissions}
    types = {p.get("type") for p in permissions}
    if "anyone" in types:
        return "public"
    if "domain" in types:
        return "domain"
    if len(permissions) > 1:
        return "shared"
    return "private"


class DriveFTSIndexer:
    """Drive → Qdrant full-text/semantic indexer."""

    def __init__(self):
        self._embedder = TextEmbedding(model_name=EMBEDDING_MODEL)
        self.qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=120)
        self._drive_service = None
        self._ensure_collection()

    # -- setup ----------------------------------------------------------

    def _ensure_collection(self):
        try:
            self.qdrant.get_collection(COLLECTION)
        except (UnexpectedResponse, Exception):
            self.qdrant.create_collection(
                collection_name=COLLECTION,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
        # Full-text index on content + name for literal keyword matching (MatchText).
        for field in ("content", "name"):
            try:
                self.qdrant.create_payload_index(
                    collection_name=COLLECTION,
                    field_name=field,
                    field_schema=PayloadSchemaType.TEXT,
                )
            except Exception:
                pass  # already indexed
        for field in ("file_type", "owner", "access_level"):
            try:
                self.qdrant.create_payload_index(
                    collection_name=COLLECTION,
                    field_name=field,
                    field_schema=PayloadSchemaType.KEYWORD,
                )
            except Exception:
                pass
        try:
            self.qdrant.create_payload_index(
                collection_name=COLLECTION,
                field_name="modified_ts",
                field_schema=PayloadSchemaType.FLOAT,
            )
        except Exception:
            pass

    def _get_drive_service(self):
        if self._drive_service is not None:
            return self._drive_service
        if not DRIVE_TOKEN_FILE.exists():
            raise RuntimeError(f"Drive token not found at {DRIVE_TOKEN_FILE}")
        creds = Credentials.from_authorized_user_file(str(DRIVE_TOKEN_FILE), DRIVE_SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            DRIVE_TOKEN_FILE.write_text(creds.to_json())
        self._drive_service = build("drive", "v3", credentials=creds)
        return self._drive_service

    # -- Drive walk -------------------------------------------------------

    FIELDS = (
        "id, name, mimeType, modifiedTime, createdTime, size, "
        "owners(displayName,emailAddress), permissions(type,role)"
    )

    def _list_children(self, folder_id: str) -> list[dict]:
        service = self._get_drive_service()
        out, page_token = [], None
        while True:
            resp = (
                service.files()
                .list(
                    q=f"'{folder_id}' in parents and trashed = false",
                    pageSize=200,
                    pageToken=page_token,
                    fields=f"nextPageToken, files({self.FIELDS})",
                )
                .execute()
            )
            out.extend(resp.get("files", []))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return out

    def walk_folder(self, folder_id: str, path: str = "") -> list[dict]:
        """Recursively list all non-folder files under folder_id, tagged with drive_path."""
        files: list[dict] = []
        for entry in self._list_children(folder_id):
            entry_path = f"{path}/{entry['name']}" if path else entry["name"]
            if entry.get("mimeType") == FOLDER_MIME:
                files.extend(self.walk_folder(entry["id"], entry_path))
            else:
                entry["drive_path"] = entry_path
                files.append(entry)
        return files

    # -- content extraction ------------------------------------------------

    def _extract_text(self, file_meta: dict) -> str:
        """Best-effort text extraction. Returns '' if content is unreadable (e.g. images)."""
        service = self._get_drive_service()
        mime = file_meta.get("mimeType", "")
        file_id = file_meta["id"]
        try:
            if mime == "application/vnd.google-apps.document":
                data = service.files().export(fileId=file_id, mimeType=GOOGLE_DOC_EXPORT).execute()
                return data.decode("utf-8", errors="replace")
            if mime == "application/vnd.google-apps.spreadsheet":
                data = service.files().export(fileId=file_id, mimeType=GOOGLE_SHEET_EXPORT).execute()
                return data.decode("utf-8", errors="replace")
            if mime in (
                "text/plain",
                "text/markdown",
                "application/json",
                "text/csv",
            ):
                buf = io.BytesIO()
                downloader = MediaIoBaseDownload(buf, service.files().get_media(fileId=file_id))
                done = False
                while not done:
                    _, done = downloader.next_chunk()
                return buf.getvalue().decode("utf-8", errors="replace")
            if mime == "application/pdf":
                return self._extract_pdf(service, file_id)
            if mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                return self._extract_docx(service, file_id)
        except Exception:
            return ""
        return ""  # images, slides, unsupported types — metadata-only indexing

    @staticmethod
    def _extract_pdf(service, file_id: str) -> str:
        import pdfplumber

        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, service.files().get_media(fileId=file_id))
        done = False
        while not done:
            _, done = downloader.next_chunk()
        buf.seek(0)
        text_parts = []
        with pdfplumber.open(buf) as pdf:
            for page in pdf.pages[:50]:  # cap runaway PDFs
                text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts)

    @staticmethod
    def _extract_docx(service, file_id: str) -> str:
        import docx

        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, service.files().get_media(fileId=file_id))
        done = False
        while not done:
            _, done = downloader.next_chunk()
        buf.seek(0)
        document = docx.Document(buf)
        return "\n".join(p.text for p in document.paragraphs)

    # -- embedding ----------------------------------------------------------

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [e.tolist() for e in self._embedder.embed(texts)]

    # -- indexing -------------------------------------------------------

    def index_file(self, file_meta: dict, root_label: str) -> int:
        """Index (or re-index) a single Drive file. Returns chunk count."""
        file_id = file_meta["id"]
        name = file_meta.get("name", "")

        # Clear stale chunks for this file before re-indexing.
        self.qdrant.delete(
            collection_name=COLLECTION,
            points_selector=Filter(
                must=[FieldCondition(key="file_id", match=MatchValue(value=file_id))]
            ),
        )

        text = self._extract_text(file_meta)
        if len(text) > MAX_FILE_CHARS:
            text = text[:MAX_FILE_CHARS]
        chunks = _chunk_text(text)
        if not chunks:
            chunks = [""]  # index metadata-only row so the file is still findable by name

        owners = file_meta.get("owners") or []
        owner_email = owners[0].get("emailAddress", "") if owners else ""
        permissions = file_meta.get("permissions") or []
        access_level = _access_level_from_permissions(permissions, owners)
        modified_iso = file_meta.get("modifiedTime", "")
        created_iso = file_meta.get("createdTime", "")
        modified_ts = _iso_to_ts(modified_iso)

        vectors = self._embed_texts(chunks) if any(chunks) else [[0.0] * VECTOR_SIZE for _ in chunks]

        points = []
        for i, (chunk, vec) in enumerate(zip(chunks, vectors)):
            points.append(
                PointStruct(
                    id=_point_id(file_id, i),
                    vector=vec,
                    payload={
                        "file_id": file_id,
                        "name": name,
                        "content": chunk,
                        "chunk_index": i,
                        "drive_path": file_meta.get("drive_path", name),
                        "root": root_label,
                        "file_type": _file_type_from_mime(file_meta.get("mimeType", "")),
                        "mime_type": file_meta.get("mimeType", ""),
                        "created_date": created_iso,
                        "modified_date": modified_iso,
                        "modified_ts": modified_ts,
                        "owner": owner_email,
                        "access_level": access_level,
                        "web_link": f"https://drive.google.com/file/d/{file_id}/view",
                        "indexed_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
            )
        self.qdrant.upsert(collection_name=COLLECTION, points=points)
        return len(points)

    def index_roots(self, roots: dict[str, str] | None = None) -> dict:
        """Full (re)index of the given root folders (default: KB + Client Files)."""
        roots = roots or DEFAULT_ROOTS
        stats = {"folders": len(roots), "files": 0, "chunks": 0, "errors": 0}
        for label, folder_id in roots.items():
            try:
                files = self.walk_folder(folder_id, path=label)
            except Exception as e:
                stats["errors"] += 1
                print(f"[drive_fts] failed to walk {label} ({folder_id}): {e}", file=sys.stderr)
                continue
            for file_meta in files:
                try:
                    n = self.index_file(file_meta, root_label=label)
                    stats["files"] += 1
                    stats["chunks"] += n
                except Exception as e:
                    stats["errors"] += 1
                    print(f"[drive_fts] failed to index {file_meta.get('name')}: {e}", file=sys.stderr)
        return stats

    # -- search ---------------------------------------------------------

    def search_drive(
        self,
        query: str,
        filters: dict | None = None,
        top_k: int = 10,
    ) -> list[dict]:
        """Search indexed Drive content.

        filters: {
            "file_type": "pdf" | "google_doc" | ...,
            "owner": "email@example.com",
            "date_range": {"days": 30} or {"since": iso, "until": iso},
        }
        Ranks by vector similarity; keyword presence (MatchText on content/name)
        is applied as a hard filter when the query looks like a keyword phrase
        (default: soft — vector-only) unless `keyword_required=True` is passed
        via filters.
        """
        filters = filters or {}
        must: list = []

        if filters.get("file_type"):
            must.append(FieldCondition(key="file_type", match=MatchValue(value=filters["file_type"])))
        if filters.get("owner"):
            must.append(FieldCondition(key="owner", match=MatchValue(value=filters["owner"])))
        if filters.get("access_level"):
            must.append(FieldCondition(key="access_level", match=MatchValue(value=filters["access_level"])))

        date_range = filters.get("date_range")
        if date_range:
            if "days" in date_range:
                since_ts = (datetime.now(timezone.utc) - timedelta(days=date_range["days"])).timestamp()
                must.append(FieldCondition(key="modified_ts", range=Range(gte=since_ts)))
            else:
                gte = _iso_to_ts(date_range["since"]) if date_range.get("since") else None
                lte = _iso_to_ts(date_range["until"]) if date_range.get("until") else None
                must.append(FieldCondition(key="modified_ts", range=Range(gte=gte, lte=lte)))

        if filters.get("keyword_required"):
            must.append(FieldCondition(key="content", match=MatchText(text=query)))

        q_filter = Filter(must=must) if must else None
        q_vec = self._embed_texts([query])[0]
        results = self.qdrant.query_points(
            collection_name=COLLECTION,
            query=q_vec,
            query_filter=q_filter,
            limit=top_k,
        ).points

        out = []
        for hit in results:
            p = hit.payload or {}
            out.append(
                {
                    "name": p.get("name"),
                    "drive_path": p.get("drive_path"),
                    "file_type": p.get("file_type"),
                    "owner": p.get("owner"),
                    "access_level": p.get("access_level"),
                    "created_date": p.get("created_date"),
                    "modified_date": p.get("modified_date"),
                    "web_link": p.get("web_link"),
                    "score": round(hit.score, 4),
                    "excerpt": (p.get("content") or "")[:400],
                }
            )
        return out


def _iso_to_ts(iso_str: str) -> float | None:
    if not iso_str:
        return None
    try:
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Drive Intelligence Indexer")
    sub = parser.add_subparsers(dest="command")

    p_index = sub.add_parser("index", help="(Re)index Drive roots into Qdrant")
    p_index.add_argument("--folder", help="Single folder ID to reindex (default: all roots)")
    p_index.add_argument("--label", default="custom", help="Root label for --folder")

    p_search = sub.add_parser("search", help="Search indexed Drive content")
    p_search.add_argument("query")
    p_search.add_argument("--file-type", dest="file_type")
    p_search.add_argument("--owner")
    p_search.add_argument("--days", type=int, help="Only files modified in the last N days")
    p_search.add_argument("--top-k", type=int, default=10)

    args = parser.parse_args()

    if args.command == "index":
        indexer = DriveFTSIndexer()
        t0 = time.time()
        if args.folder:
            files = indexer.walk_folder(args.folder, path=args.label)
            stats = {"folders": 1, "files": 0, "chunks": 0, "errors": 0}
            for f in files:
                try:
                    n = indexer.index_file(f, root_label=args.label)
                    stats["files"] += 1
                    stats["chunks"] += n
                except Exception as e:
                    stats["errors"] += 1
                    print(f"[drive_fts] failed to index {f.get('name')}: {e}", file=sys.stderr)
        else:
            stats = indexer.index_roots()
        stats["elapsed_s"] = round(time.time() - t0, 1)
        print(json.dumps(stats, indent=2))

    elif args.command == "search":
        indexer = DriveFTSIndexer()
        filters = {}
        if args.file_type:
            filters["file_type"] = args.file_type
        if args.owner:
            filters["owner"] = args.owner
        if args.days:
            filters["date_range"] = {"days": args.days}
        t0 = time.time()
        results = indexer.search_drive(args.query, filters=filters, top_k=args.top_k)
        elapsed = time.time() - t0
        print(f"({elapsed:.3f}s, {len(results)} results)\n")
        for i, r in enumerate(results, 1):
            print(f"--- {i}. {r['name']} (score {r['score']}) ---")
            print(f"  path: {r['drive_path']}  type: {r['file_type']}  modified: {r['modified_date']}")
            print(f"  owner: {r['owner']}  access: {r['access_level']}  link: {r['web_link']}")
            if r["excerpt"].strip():
                print(f"  excerpt: {r['excerpt'][:200]}...")
            print()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
