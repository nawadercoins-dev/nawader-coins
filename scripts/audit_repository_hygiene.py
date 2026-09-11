from pathlib import Path
from collections import defaultdict
import hashlib, json, re

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {'.git', '__pycache__', 'node_modules'}

files = []
for p in ROOT.rglob('*'):
    if not p.is_file():
        continue
    if any(part in SKIP_DIRS for part in p.parts):
        continue
    rel = p.relative_to(ROOT).as_posix()
    files.append((rel, p))

by_hash = defaultdict(list)
for rel, p in files:
    try:
        data = p.read_bytes()
    except Exception:
        continue
    by_hash[hashlib.sha256(data).hexdigest()].append(rel)

identical = [sorted(v) for v in by_hash.values() if len(v) > 1]
version_like = sorted(rel for rel, _ in files if re.search(r'(?:^|[._-])(?:v|r)\d', rel, re.I))
patch_helpers = sorted(rel for rel, _ in files if rel.startswith(('scripts/patch_', '.github/workflows/apply-')))
root_legacy = sorted(rel for rel, _ in files if '/' not in rel and (rel.startswith('#U') or '~' in rel or re.search(r'V\d', rel, re.I)))

report = {
    'total_files': len(files),
    'identical_groups': identical,
    'version_named_files': version_like,
    'patch_and_apply_files': patch_helpers,
    'root_legacy_candidates': root_legacy,
    'protected_core': ['server.py', 'admin/index.html', 'admin/app.js', 'admin/styles.css'],
    'note': 'Audit only. This script never deletes or edits project files.'
}

out = ROOT / 'repository_hygiene_report.json'
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({
    'total_files': report['total_files'],
    'identical_groups': len(identical),
    'version_named_files': len(version_like),
    'patch_and_apply_files': len(patch_helpers),
    'root_legacy_candidates': len(root_legacy),
    'report': str(out.relative_to(ROOT))
}, ensure_ascii=False, indent=2))
