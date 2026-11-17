#!/usr/bin/env python3
"""Read CCSN's public search/detail/PDF endpoints; no login, bulk sync or KB mutation."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import urllib.parse

BASE = 'https://www.ccsn.org.cn/newweb/'
MAX_BYTES = 80 * 1024 * 1024

def request(path, fields=None):
    url = BASE + path
    cmd = ['curl', '--fail', '--silent', '--show-error', '--location',
           '--connect-timeout', '10', '--max-time', '45', '--max-filesize', str(MAX_BYTES), url]
    if fields is not None:
        cmd += ['--data', urllib.parse.urlencode(fields)]
    p = subprocess.run(cmd, capture_output=True, timeout=50)
    if p.returncode:
        raise RuntimeError('网站读取失败: ' + p.stderr.decode(errors='replace')[:400])
    if len(p.stdout) > MAX_BYTES:
        raise RuntimeError('响应超过单次读取上限')
    return p.stdout

def data(path, fields):
    obj = json.loads(request(path, fields))
    if not isinstance(obj, dict):
        raise RuntimeError('网站返回结构变化，请改用浏览器并更新接入方式')
    return obj

def summary(item):
    return {k: item.get(k) for k in ('Guid', 'StandardCode', 'StandardCNName',
            'StandardState', 'PublishDate', 'PerformDate', 'AbolishDate')}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    q = sub.add_parser('search'); q.add_argument('keyword'); q.add_argument('--page', type=int, default=1)
    f = sub.add_parser('fetch'); f.add_argument('guid'); f.add_argument('--out', required=True); f.add_argument('--keep-fulltext', action='store_true', help='仅明确要求归档时将全文长期保存在输出目录')
    args = ap.parse_args()
    if args.command == 'search':
        result = data('api/StandardQuery.assx/queryStandard',
                      {'gjz': args.keyword, 'pageIndex': args.page, 'pageSize': 10})
        if not isinstance(result.get('List'), list) or 'Total' not in result:
            raise RuntimeError('检索接口结构异常；不能视为零结果')
        print(json.dumps({'total': result['Total'], 'page': args.page,
                          'items': [summary(i) for i in result['List']]}, ensure_ascii=False, indent=2))
        return
    if not re.fullmatch(r'[0-9a-fA-F-]{36}', args.guid):
        raise ValueError('请使用检索结果返回的Guid')
    out = Path(args.out).resolve()
    if out.exists():
        raise ValueError('输出目录已存在，请指定新目录以保留旧证据')
    item = data('api/StandardQuery.assx/queryStandardByGuid', {'guid': args.guid})
    if not item.get('StandardCode') or not item.get('StandardCNName'):
        raise RuntimeError('详情未返回标准身份，不能继续')
    detail_url = BASE + 'standardQuery?' + urllib.parse.urlencode({'guid': args.guid, 'showDetail': 'true'})
    manifest = {'accessed_at': dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(),
                'source': 'CCSN public endpoints', 'detail_url': detail_url,
                'standard': summary(item), 'status': 'metadata_only',
                'legal_applicability': 'not_verified', 'visual_review': 'not_started'}
    out.mkdir(parents=True)
    (out / 'detail.json').write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding='utf-8')
    working = out if args.keep_fulltext else Path(tempfile.mkdtemp(prefix='gusu-standard-'))
    manifest['retention'] = 'archive_fulltext' if args.keep_fulltext else 'links_only'
    file_id = item.get('FullTextFile')
    try:
        if not file_id:
            manifest['reason'] = '网站详情未提供FullTextFile；需另查正式全文'
        else:
            if not re.fullmatch(r'[0-9a-fA-F-]{32,36}', file_id):
                raise RuntimeError('附件标识结构变化')
            path = 'api/AccessoryMgeSvr.assx/getFile?' + urllib.parse.urlencode({'id': file_id})
            raw = request(path)
            if not raw.startswith(b'%PDF-'):
                raise RuntimeError('附件不是PDF；不得将HTML或错误页面作为全文')
            (working / 'standard.pdf').write_bytes(raw)
            manifest.update(status='pdf_fetched', pdf_url=BASE + path,
                            sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
            try:
                from pypdf import PdfReader
                reader = PdfReader(working / 'standard.pdf')
                manifest['pages'] = len(reader.pages)
                # Extracted text may look nonempty yet be corrupted. It is never authority.
                texts = [f'=== PDF物理页 {i+1} ===\n' + (p.extract_text() or '') for i,p in enumerate(reader.pages)]
                (working / 'text-index.txt').write_text('\n\n'.join(texts), encoding='utf-8')
                manifest['text_index'] = '仅用于定位，可能乱码；引用前须视觉核对原页'
            except Exception as exc:
                manifest['text_index'] = '未生成: ' + str(exc)[:180]
    except Exception as exc:
        manifest.update(status='fulltext_failed', reason=str(exc))
    (out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({**manifest, 'temporary_working_directory': str(working) if not args.keep_fulltext else None}, ensure_ascii=False, indent=2))
    if manifest['status'] != 'pdf_fetched':
        sys.exit(2)

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'status': 'failed', 'reason': str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
