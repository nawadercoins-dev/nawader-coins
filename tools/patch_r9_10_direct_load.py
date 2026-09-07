from pathlib import Path
p=Path('admin/index.html')
s=p.read_text(encoding='utf-8')
s=s.replace('/admin/admin-ui-stability-r9.8.css?v=5.6.2-r9.8','/admin/admin-ui-stability-r9.9.css?v=5.6.2-r9.10')
s=s.replace('<title>دار المقتنيات — الإدارة V5.6.2 R9.4</title>','<title>دار المقتنيات — الإدارة V5.6.2 R9.10</title>')
s=s.replace('<script src="/arabic_ui_guard.js?v=1" defer></script>','<script src="/arabic_ui_guard.js?v=5.6.2-r9.10" defer></script>\n<script src="/admin/admin-r9.9-records.js?v=5.6.2-r9.10" defer></script>')
p.write_text(s,encoding='utf-8')
