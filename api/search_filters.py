"""SQL WHERE-clause builder for search filter parameters.

build_filters(p: dict) -> tuple[list[str], dict]
  Returns (where_clauses, bind_params).
  Caller joins clauses with AND and merges params into the query dict.
  All SQL is parameterized — no string interpolation.

Supported keys in p:
  ext         CSV extensions: "jpg,png" or ".jpg,.png"
  folder      single folder token (folder_tokens GIN @>)
  role        CSV roles: "poster,banner" (role_hint &&)
  year_from   int — year_hint lower bound
  year_to     int — year_hint upper bound
  size_min_mb float — size_bytes lower bound (MB → bytes)
  size_max_mb float — size_bytes upper bound
  mtime_from  ISO date string — mtime lower bound
  mtime_to    ISO date string — mtime upper bound
  tag         CSV tag names — asset must have ALL listed tags (AND)
"""


def build_filters(p: dict) -> tuple[list[str], dict]:
    clauses: list[str] = []
    params: dict = {}

    if p.get('ext'):
        exts = [e.strip().lower() for e in p['ext'].split(',') if e.strip()]
        exts = [e if e.startswith('.') else f'.{e}' for e in exts]
        if exts:
            clauses.append("a.primary_ext = ANY(%(ext_arr)s)")
            params['ext_arr'] = exts

    if p.get('folder'):
        folder = p['folder'].strip()
        if folder:
            clauses.append("a.folder_tokens @> %(folder_arr)s")
            params['folder_arr'] = [folder]

    if p.get('role'):
        roles = [r.strip().lower() for r in p['role'].split(',') if r.strip()]
        if roles:
            clauses.append("a.role_hint && %(role_arr)s")
            params['role_arr'] = roles

    if p.get('year_from') is not None:
        clauses.append("a.year_hint >= %(year_from)s")
        params['year_from'] = int(p['year_from'])

    if p.get('year_to') is not None:
        clauses.append("a.year_hint <= %(year_to)s")
        params['year_to'] = int(p['year_to'])

    if p.get('size_min_mb') is not None:
        clauses.append("a.size_bytes >= %(size_min)s")
        params['size_min'] = int(float(p['size_min_mb']) * 1024 * 1024)

    if p.get('size_max_mb') is not None:
        clauses.append("a.size_bytes <= %(size_max)s")
        params['size_max'] = int(float(p['size_max_mb']) * 1024 * 1024)

    if p.get('mtime_from'):
        clauses.append("a.mtime >= %(mtime_from)s::timestamptz")
        params['mtime_from'] = p['mtime_from']

    if p.get('mtime_to'):
        clauses.append("a.mtime <= %(mtime_to)s::timestamptz")
        params['mtime_to'] = p['mtime_to']

    if p.get('tag'):
        tag_names = [t.strip() for t in p['tag'].split(',') if t.strip()]
        for i, tname in enumerate(tag_names):
            key = f'tag_{i}'
            clauses.append(f"""
                EXISTS (
                    SELECT 1 FROM asset_tags at_{i}
                    JOIN tags t_{i} ON t_{i}.id = at_{i}.tag_id
                    WHERE at_{i}.asset_id = a.id AND t_{i}.name = %({key})s
                )
            """)
            params[key] = tname

    return clauses, params
