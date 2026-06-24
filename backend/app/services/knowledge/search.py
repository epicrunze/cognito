# backend/app/services/knowledge/search.py
"""Read-side queries over the materialized concept cache: FTS, detail, graph, index."""

import json
import sqlite3


def search_concepts(conn: sqlite3.Connection, q: str, type: str | None = None,
                    source: str | None = None, limit: int = 20) -> list[dict]:
    """Full-text search ranked by bm25, with optional type/source filters."""
    sql = [
        "SELECT f.concept_id, c.type, c.source, c.title, c.description,",
        "       snippet(concepts_fts, 4, '[', ']', '…', 12) AS snip",
        "FROM concepts_fts f JOIN concepts c ON c.concept_id = f.concept_id",
        "WHERE concepts_fts MATCH ?",
    ]
    params: list = [q]
    if type is not None:
        sql.append("AND c.type = ?")
        params.append(type)
    if source is not None:
        sql.append("AND c.source = ?")
        params.append(source)
    sql.append("ORDER BY bm25(concepts_fts) LIMIT ?")
    params.append(limit)
    rows = conn.execute(" ".join(sql), params).fetchall()
    return [
        {"concept_id": r[0], "type": r[1], "source": r[2], "title": r[3],
         "description": r[4], "snippet": r[5]}
        for r in rows
    ]


def concept_detail(conn: sqlite3.Connection, concept_id: str) -> dict | None:
    row = conn.execute(
        "SELECT concept_id, source, type, title, description, resource, tags, "
        "timestamp, frontmatter, body FROM concepts WHERE concept_id = ?",
        (concept_id,),
    ).fetchone()
    if not row:
        return None
    links = [r[0] for r in conn.execute(
        "SELECT dst_id FROM concept_links WHERE src_id = ? ORDER BY dst_id", (concept_id,)
    ).fetchall()]
    backlinks = [r[0] for r in conn.execute(
        "SELECT src_id FROM concept_links WHERE dst_id = ? ORDER BY src_id", (concept_id,)
    ).fetchall()]
    return {
        "concept_id": row[0], "source": row[1], "type": row[2], "title": row[3],
        "description": row[4], "resource": row[5], "tags": json.loads(row[6] or "[]"),
        "timestamp": row[7], "frontmatter": json.loads(row[8] or "{}"), "body": row[9],
        "links": links, "backlinks": backlinks,
    }


def graph(conn: sqlite3.Connection, root: str | None = None, depth: int | None = None) -> dict:
    """Whole graph, or BFS from *root* to *depth* hops over the link edges."""
    all_edges = conn.execute("SELECT src_id, dst_id FROM concept_links").fetchall()
    if root is None:
        node_rows = conn.execute(
            "SELECT concept_id, type, source, title FROM concepts ORDER BY concept_id"
        ).fetchall()
        # Intentional asymmetry: whole-graph includes broken-link edges to nonexistent nodes
        # (per spec §10 — UI renders them faintly); the rooted BFS below is node-bounded.
        edges = [{"src": s, "dst": d} for (s, d) in all_edges]
    else:
        adj: dict[str, set[str]] = {}
        for s, d in all_edges:
            adj.setdefault(s, set()).add(d)
            adj.setdefault(d, set()).add(s)
        node_ids = {root}
        frontier = {root}
        hop = 0
        while depth is None or hop < depth:
            nxt: set[str] = set()
            for n in frontier:
                nxt |= adj.get(n, set()) - node_ids
            if not nxt:
                break
            node_ids |= nxt
            frontier = nxt
            hop += 1
        edges = [{"src": s, "dst": d} for (s, d) in all_edges
                 if s in node_ids and d in node_ids]
        node_rows = conn.execute(
            "SELECT concept_id, type, source, title FROM concepts WHERE concept_id IN (%s)"
            " ORDER BY concept_id" % ",".join("?" * len(node_ids)),
            tuple(node_ids),
        ).fetchall()
    nodes = [{"concept_id": r[0], "type": r[1], "source": r[2], "title": r[3]}
             for r in node_rows]
    return {"nodes": nodes, "edges": edges}


def synth_index(conn: sqlite3.Connection) -> str:
    """Synthesize an OKF index.md grouping concepts by type (progressive disclosure)."""
    rows = conn.execute(
        "SELECT type, concept_id, title, description FROM concepts ORDER BY type, concept_id"
    ).fetchall()
    groups: dict[str, list] = {}
    for ctype, cid, title, desc in rows:
        groups.setdefault(ctype, []).append((cid, title, desc))
    out: list[str] = []
    for ctype in sorted(groups):
        out.append(f"# {ctype}")
        out.append("")
        for cid, title, desc in groups[ctype]:
            label = title or cid
            tail = f" - {desc}" if desc else ""
            out.append(f"* [{label}](/{cid}.md){tail}")
        out.append("")
    return "\n".join(out).strip()
