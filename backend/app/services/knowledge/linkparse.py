"""Extract intra-bundle markdown links and resolve them to concept ids.

A concept id is a file path minus the .md suffix. Absolute links begin with
'/' (bundle-relative); relative links resolve against the linking concept's
directory. External (http/https) links are ignored for the graph.
"""

import posixpath
import re

_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def extract_links(body: str, base_id: str) -> list[str]:
    """Return resolved, de-duplicated concept ids linked from *body*.

    *base_id* is the concept id of the document containing the links; its
    directory is the resolution root for relative links.
    """
    base_dir = posixpath.dirname(base_id)
    out: list[str] = []
    seen: set[str] = set()
    for raw in _LINK_RE.findall(body):
        target = raw.split("#", 1)[0]  # drop anchor fragment
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        if target.startswith("/"):
            path = target.lstrip("/")
        else:
            path = posixpath.normpath(posixpath.join(base_dir, target))
        if path.endswith(".md"):
            path = path[:-3]
        if path and path not in seen:
            seen.add(path)
            out.append(path)
    return out
