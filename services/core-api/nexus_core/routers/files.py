"""Files: browse + text search, jailed to configured storage roots.

Fixes security error C5: the old endpoints defaulted to Path.home() and
accepted any path, walked arbitrary directories and read any small text
file — exposing the whole home directory to any LAN device. Here every
requested path is resolved and must stay inside settings.storage_roots;
traversal attempts and symlink escapes are rejected with 403.
"""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import log_activity
from ..models import User
from ..schemas import FileInfo, SearchResult
from ..security import get_current_user, require_scope
from ..settings import get_settings

router = APIRouter(prefix="/files", tags=["files"])


def _resolve_jailed_path(path: str | None) -> Path:
    """Resolve a user-supplied path and ensure it stays inside a storage root."""
    settings = get_settings()
    roots = [Path(r).resolve() for r in settings.storage_roots]
    if not roots:
        raise HTTPException(status_code=403, detail="No storage roots configured")

    if path:
        target = Path(path).expanduser()
        if not target.is_absolute():
            target = roots[0] / target
    else:
        target = roots[0]

    resolved = target.resolve()  # resolves .. and symlinks
    if not any(resolved == root or resolved.is_relative_to(root) for root in roots):
        raise HTTPException(status_code=403, detail="Path outside storage roots")
    return resolved


@router.get("/roots", response_model=list[str])
def storage_roots(current_user: User = Depends(get_current_user)):
    """Report the jailed roots so clients can render a file picker."""
    return get_settings().storage_roots


@router.get("/browse", response_model=list[FileInfo])
def browse_files(
    path: str | None = None,
    current_user: User = Depends(require_scope("read", "filesystem")),
):
    target_dir = _resolve_jailed_path(path)
    if not target_dir.exists() or not target_dir.is_dir():
        raise HTTPException(status_code=404, detail="Directory not found")

    settings = get_settings()
    files = []
    try:
        for entry in target_dir.iterdir():
            try:
                is_dir = entry.is_dir()
                # Never report paths that escape the jail via symlink
                resolved = entry.resolve()
                if not any(resolved == r or resolved.is_relative_to(r) for r in [Path(x).resolve() for x in settings.storage_roots]):
                    continue
                files.append(
                    {
                        "name": entry.name,
                        "path": str(resolved),
                        "is_dir": is_dir,
                        "size": 0 if is_dir else entry.stat().st_size,
                    }
                )
            except (PermissionError, FileNotFoundError):
                continue
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")

    return sorted(files, key=lambda x: (not x["is_dir"], x["name"].lower()))


@router.get("/search", response_model=list[SearchResult])
def search_files(
    query: str,
    path: str | None = None,
    current_user: User = Depends(require_scope("read", "filesystem")),
):
    # Validate the path BEFORE any early return: a jail escape attempt must
    # be rejected even when the query itself is too short to search for.
    target_dir = _resolve_jailed_path(path)
    if not query or len(query) < 2:
        return []
    if not target_dir.exists() or not target_dir.is_dir():
        raise HTTPException(status_code=404, detail="Directory not found")

    settings = get_settings()
    results = []
    query_lower = query.lower()
    roots = [Path(r).resolve() for r in settings.storage_roots]

    for root, dirs, files in _limited_walk(target_dir, settings.max_search_depth):
        # Prune directories outside the jail or too deep; skip hidden dirs
        dirs[:] = [
            d
            for d in dirs
            if not d.startswith(".") and _resolve_jailed_path(str(Path(root) / d)) is not None
        ]
        for file in files:
            if file.startswith("."):
                continue
            file_path = Path(root) / file
            try:
                if file_path.stat().st_size > 1_000_000:
                    continue
                with file_path.open("r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if query_lower in line.lower():
                            results.append(
                                {"path": str(file_path), "match_context": line.strip()[:100]}
                            )
                            break  # one match per file
            except (PermissionError, FileNotFoundError, IsADirectoryError, OSError):
                continue
            if len(results) >= settings.max_search_results:
                return results
    return results


def _limited_walk(top: Path, max_depth: int):
    """os.walk with a depth cap so search cannot crawl the entire disk."""
    base_depth = len(top.resolve().parts)
    for root, dirs, files in _walk(top):
        if len(Path(root).resolve().parts) - base_depth > max_depth:
            dirs[:] = []
            continue
        yield root, dirs, files


def _walk(top: Path):
    import os

    for root, dirs, files in os.walk(top, followlinks=False):
        yield root, dirs, files


@router.post("/upload", response_model=FileInfo)
async def upload_file(
    file: UploadFile = File(...),
    directory: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_scope("write", "filesystem")),
):
    target_dir = _resolve_jailed_path(directory)
    if not target_dir.exists() or not target_dir.is_dir():
        raise HTTPException(status_code=400, detail="Target directory does not exist")
    safe_filename = Path(file.filename or "upload").name
    dest_path = (target_dir / safe_filename).resolve()
    roots = [Path(r).resolve() for r in get_settings().storage_roots]
    if not any(dest_path == root or dest_path.is_relative_to(root) for root in roots):
        raise HTTPException(status_code=403, detail="Path outside storage roots")

    content = await file.read()
    dest_path.write_bytes(content)
    log_activity(db, user_id=current_user.id, action="file.uploaded", detail=safe_filename)
    db.commit()
    return {
        "name": dest_path.name,
        "path": str(dest_path),
        "is_dir": False,
        "size": len(content),
    }


@router.get("/download")
def download_file(
    path: str,
    current_user: User = Depends(require_scope("read", "filesystem")),
):
    target_file = _resolve_jailed_path(path)
    if not target_file.exists() or not target_file.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=str(target_file), filename=target_file.name)


@router.delete("/delete")
def delete_file(
    path: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_scope("write", "filesystem")),
):
    target_file = _resolve_jailed_path(path)
    if not target_file.exists():
        raise HTTPException(status_code=404, detail="Target not found")
    if target_file.is_dir():
        raise HTTPException(status_code=400, detail="Cannot delete directory with this endpoint")
    filename = target_file.name
    target_file.unlink()
    log_activity(db, user_id=current_user.id, action="file.deleted", detail=filename)
    db.commit()
    return {"status": "deleted", "path": str(target_file)}

