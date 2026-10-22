"""Serve only the content-hashed files in a published local research manifest."""
import hashlib
import json
import re


def latest_manifest(root):
    path=root/'outputs/research/latest.json'
    if not path.exists():raise FileNotFoundError('Chưa xuất báo cáo. Chạy python manage.py research trong thư mục dự án.')
    manifest=json.loads(path.read_text(encoding='utf-8'))
    if not re.fullmatch('[0-9a-f]{64}',manifest['research_id']):raise ValueError('Research manifest không hợp lệ.')
    return manifest


def artifact(root,name):
    if not re.fullmatch(r'[a-zA-Z0-9_.-]{1,100}',name):raise FileNotFoundError('Tên file không hợp lệ.')
    manifest=latest_manifest(root)
    entry=next((row for row in manifest['files'] if row['name']==name),None)
    if entry is None:raise FileNotFoundError('File không có trong research manifest.')
    path=root/'outputs/research'/manifest['research_id']/name
    data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=entry['sha256']:raise ValueError('Hash file nghiên cứu không khớp manifest; cần xuất lại.')
    return data
