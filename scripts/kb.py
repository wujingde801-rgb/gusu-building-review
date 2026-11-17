#!/usr/bin/env python3
"""Independent, revisioned knowledge store. Only apply mutates the live catalog."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import uuid
import zipfile

LAYERS = {'A', 'B', 'C', 'D'}
STATUSES = {'unverified', 'effective', 'future', 'repealed', 'superseded', 'archived'}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def dump(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, indent=2)

def today():
    return dt.date.today().isoformat()

def connect(root):
    root = Path(root).resolve()
    if not (root / 'catalog.sqlite').is_file():
        raise ValueError('知识库不存在；先 init')
    c = sqlite3.connect(root / 'catalog.sqlite', timeout=30)
    c.row_factory = sqlite3.Row
    return c

def init(root):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    for d in ('originals', 'pending', 'archive', 'exports'):
        (root / d).mkdir(exist_ok=True)
    c = sqlite3.connect(root / 'catalog.sqlite')
    c.executescript('''
    CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY, revision INTEGER NOT NULL, metadata TEXT NOT NULL, blob TEXT NOT NULL, text TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS history(id TEXT, revision INTEGER, metadata TEXT, blob TEXT, text TEXT, PRIMARY KEY(id,revision));
    CREATE TABLE IF NOT EXISTS proposals(id TEXT PRIMARY KEY, payload TEXT NOT NULL, hash TEXT NOT NULL, applied INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY, at TEXT, proposal TEXT, confirmation TEXT, hash TEXT);
    ''')
    c.commit()
    c.close()
    return {'root': str(root), 'schema': 1}

def metadata(m):
    m = dict(m)
    for field in ('title', 'layer', 'version', 'region', 'topics', 'status', 'kind'):
        if field not in m or m[field] in ('', None):
            raise ValueError('缺少元数据: ' + field)
    if m['layer'] not in LAYERS or m['status'] not in STATUSES:
        raise ValueError('非法 layer/status')
    if m['kind'] not in {'standard', 'policy', 'checklist', 'interpretation', 'experience', 'rule'}:
        raise ValueError('非法 kind')
    if not isinstance(m['topics'], list):
        raise ValueError('topics 必须为数组')
    for k in ('effective_on', 'expires_on', 'verified_on'):
        if m.get(k):
            dt.date.fromisoformat(m[k])
    if m['status'] == 'effective' and m['layer'] == 'B':
        if m['kind'] not in {'standard', 'policy'} or not all(m.get(k) for k in ('official_url','issuer','verified_on','effective_on','verification_note')):
            raise ValueError('有效B来源需正式网址、发布机关、实施/核验日期及核验说明')
        if not m['official_url'].startswith('https://'):
            raise ValueError('官方来源须 HTTPS；域名及发文身份仍需人工核验')
    return m

def propose(root, operation, file=None, meta=None, record=None, text_file=None):
    root = Path(root).resolve()
    c = connect(root)
    old = c.execute('SELECT * FROM records WHERE id=?', (record,)).fetchone() if record else None
    if operation != 'add' and old is None:
        raise ValueError('记录不存在')
    if operation=='replace' and meta is None: raise ValueError('替换原文必须提供重新核验的元数据；未核验时设unverified')
    m = metadata(meta if meta is not None else json.loads(old['metadata']))
    if operation in {'add','replace'} and not file:
        raise ValueError('add/replace 需 file')
    data = Path(file).read_bytes() if file else None
    if data is not None:
        sha = digest(data)
        dup = c.execute('SELECT id FROM records WHERE blob=?', (sha,)).fetchone()
        if dup and (operation == 'add' or dup['id'] != record):
            raise ValueError('相同原文已入库: ' + dup['id'])
    else:
        sha = old['blob']
    if operation == 'archive':
        m['status'] = 'archived'
    text = Path(text_file).read_text('utf-8') if text_file else ''
    if data is not None and not text_file and Path(file).suffix.lower() in {'.md','.txt','.json','.csv'}:
        text = data.decode('utf-8')
    if data is None:
        text = old['text']
    pid = uuid.uuid4().hex
    pending = root / 'pending' / pid
    pending.mkdir()
    if data is not None:
        (pending / 'source').write_bytes(data)
    payload = {'operation':operation, 'record':record or uuid.uuid4().hex,
               'expected_revision':old['revision'] if old else 0,
               'metadata':m, 'blob':sha, 'text':text,
               'filename':Path(file).name if file else json.loads(old['metadata']).get('filename'),
               'created':dt.datetime.now(dt.timezone.utc).isoformat()}
    token = digest(dump(payload).encode())
    c.execute('INSERT INTO proposals VALUES(?,?,?,0)', (pid,dump(payload),token))
    c.commit()
    (pending / 'proposal.json').write_text(dump({'id':pid,'confirm_token':token,**payload}),encoding='utf-8')
    return {'proposal':pid, 'confirm_token':token, **payload}

def apply(root, pid, token, confirmation):
    if not confirmation.strip():
        raise ValueError('需记录用户实际确认原文/消息标识，不能自动代填')
    root = Path(root).resolve()
    c = connect(root)
    try:
        c.execute('BEGIN IMMEDIATE')
        r = c.execute('SELECT * FROM proposals WHERE id=?',(pid,)).fetchone()
        if not r or r['applied'] or r['hash'] != token:
            raise ValueError('无效/已执行提案或确认摘要不匹配')
        p = json.loads(r['payload'])
        if digest(dump(p).encode()) != r['hash']: raise ValueError('提案内容已变化，确认摘要失效')
        old = c.execute('SELECT * FROM records WHERE id=?',(p['record'],)).fetchone()
        if (old['revision'] if old else 0) != p['expected_revision']:
            raise ValueError('提案过期：目录已变更，请重新提案')
        if p['operation']=='add':
            duplicate=c.execute('SELECT id FROM records WHERE blob=?',(p['blob'],)).fetchone()
            if duplicate: raise ValueError('相同原文已被另一提案入库: '+duplicate['id'])
        m = metadata(p['metadata'])
        m['filename'] = p['filename']
        blob = root / 'originals' / p['blob']
        staged = root / 'pending' / pid / 'source'
        if staged.exists():
            data = staged.read_bytes()
            if digest(data) != p['blob']:
                raise ValueError('暂存原文被修改')
            if not blob.exists():
                with blob.open('xb') as f:
                    f.write(data)
        if not blob.is_file() or digest(blob.read_bytes()) != p['blob']:
            raise ValueError('原文缺失或哈希不匹配')
        if old:
            c.execute('INSERT INTO history VALUES(?,?,?,?,?)',tuple(old))
            archive = root / 'archive' / (p['record'] + '-' + str(old['revision']) + '.json')
            archive.write_text(dump(dict(old)), encoding='utf-8')
        revision = p['expected_revision'] + 1
        c.execute('INSERT OR REPLACE INTO records VALUES(?,?,?,?,?)', (p['record'],revision,dump(m),p['blob'],p['text']))
        c.execute('UPDATE proposals SET applied=1 WHERE id=?',(pid,))
        c.execute('INSERT INTO audit(at,proposal,confirmation,hash) VALUES(?,?,?,?)', (dt.datetime.now(dt.timezone.utc).isoformat(),pid,confirmation,token))
        c.commit()
        return {'id':p['record'],'revision':revision,'status':m['status']}
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

def usable(m, as_of=None):
    date = dt.date.fromisoformat(as_of or today())
    if m.get('layer') != 'B' or m.get('kind') not in {'standard','policy'} or m.get('status') != 'effective':
        return False
    if not all(m.get(k) for k in ('official_url','issuer','effective_on','verified_on','verification_note')):
        return False
    start = dt.date.fromisoformat(m['effective_on'])
    verified = dt.date.fromisoformat(m['verified_on'])
    return start <= date and verified <= date and (date-verified).days <= 90 and (not m.get('expires_on') or date < dt.date.fromisoformat(m['expires_on']))

def records(root, query='', all_status=False, as_of=None):
    c = connect(root)
    rows = c.execute('SELECT * FROM records ORDER BY id').fetchall()
    result=[]
    for r in rows:
        x=dict(r); x['metadata']=json.loads(x['metadata'])
        if query.casefold() not in (dump(x['metadata'])+' '+x['text']).casefold():
            continue
        if not all_status and not usable(x['metadata'], as_of):
            continue
        x['basis_usable']=usable(x['metadata'],as_of)
        result.append(x)
    c.close()
    return result

def backup(root, dest):
    root=Path(root).resolve(); dest=Path(dest).resolve()
    if dest.is_relative_to(root):
        raise ValueError('备份必须位于知识库外，防止递归')
    if dest.exists():
        raise ValueError('备份目标已存在')
    c=connect(root)
    tmp=root/'exports'/('snapshot-'+uuid.uuid4().hex+'.sqlite')
    out=sqlite3.connect(tmp)
    c.backup(out); out.close(); c.close()
    try:
        with zipfile.ZipFile(dest,'x',zipfile.ZIP_DEFLATED) as z:
            z.write(tmp,'catalog.sqlite')
            for sub in ('originals','pending','archive'):
                for f in (root/sub).rglob('*'):
                    if f.is_file(): z.write(f,str(f.relative_to(root)))
    finally:
        tmp.unlink()
    return {'backup':str(dest),'sha256':digest(dest.read_bytes())}

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--root',required=True)
    s=p.add_subparsers(dest='command',required=True)
    s.add_parser('init')
    q=s.add_parser('propose'); q.add_argument('operation',choices=['add','replace','metadata','archive']); q.add_argument('--file'); q.add_argument('--metadata'); q.add_argument('--record'); q.add_argument('--text-file')
    q=s.add_parser('apply'); q.add_argument('proposal'); q.add_argument('--token',required=True); q.add_argument('--confirmation',required=True)
    q=s.add_parser('search'); q.add_argument('query',nargs='?',default=''); q.add_argument('--all',action='store_true'); q.add_argument('--as-of')
    q=s.add_parser('history'); q.add_argument('record')
    q=s.add_parser('backup'); q.add_argument('destination')
    a=p.parse_args()
    if a.command=='init': result=init(a.root)
    elif a.command=='propose': result=propose(a.root,a.operation,a.file,json.loads(Path(a.metadata).read_text('utf-8')) if a.metadata else None,a.record,a.text_file)
    elif a.command=='apply': result=apply(a.root,a.proposal,a.token,a.confirmation)
    elif a.command=='search': result=records(a.root,a.query,a.all,a.as_of)
    elif a.command=='backup': result=backup(a.root,a.destination)
    else:
        c=connect(a.root); result=[dict(r) for r in c.execute('SELECT * FROM history WHERE id=? ORDER BY revision',(a.record,))]; c.close()
    print(dump(result))

if __name__=='__main__':
    try: main()
    except (ValueError, OSError, sqlite3.Error) as e:
        print(str(e),file=sys.stderr); sys.exit(2)
