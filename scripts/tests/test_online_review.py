"""Synthetic regression fixtures; no real project conclusions or live KB writes."""
import base64
import copy
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import review
import kb
from pypdf import PdfWriter

class OnlineReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        pdf=self.root/'project.pdf'; w=PdfWriter(); w.add_blank_page(width=100,height=100)
        with pdf.open('wb') as f: w.write(f)
        profile={'name':'测试夹具 非真实审查','stage':'planning','protection_identity':'ordinary','heritage_work':False,'district_update':False}
        review.start(pdf,self.root/'work',profile,'detailed')
        self.state=review.read(self.root/'work/review.json'); self.state['date']='2026-11-03'
        self.state['inventory'][0]['visual_status']='seen'
        img=self.root/'e.png'; img.write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII='))
        self.state['evidence']=[{'id':'e1','source_sha256':review.hashfile(pdf),'page':1,'bbox':[0,0,1,1],'path':str(img),'sha256':review.hashfile(img),'observation':'模拟事实','quality':'clear'}]
        self.state['facts']=[{'id':'f1','observation':'模拟事实','evidence_ids':['e1']}]
        self.b={'source_type':'online','title':'模拟标准 非真实依据','standard_code':'TEST-2026','version':'2026','issuer':'测试机关','url':'https://example.org/standard','effective_on':'2026-01-01','status':'effective','clause':'1.1','excerpt':'模拟强制条文','source_locator':'PDF第5页','force':'mandatory','verification_id':'v1'}
        self.log={'id':'v1','title':self.b['title'],'standard_code':self.b['standard_code'],'version':'2026','url':self.b['url'],'accessed_on':'2026-11-03','source_authority':'official','authority_note':'模拟发布身份记录','status_checked':True,'status_url':'https://example.org/notice','status_evidence':'模拟实施与无替代核验记录','fulltext_url':'https://example.org/standard.pdf','fulltext_status':'read','fulltext_locator':'PDF第5页','reviewed_clauses':[{'clause':'1.1','source_locator':'PDF第5页','observation':'已读模拟条款与上下文'}]}
        self.state['verification_log']=[self.log]
        self.check=self.state['checks'][0]
        self.check.update(result='violation',fact_ids=['f1'],comparison='模拟比较',action='模拟修改',basis=self.b,counterevidence={'searched':['e1'],'result':'none_found','reason':'模拟反证核查'})
        for g in self.check['applicability'].values():g.update(result='pass',reason='模拟条件已核对')

    def test_online_passes_without_kb_or_pdf_cache(self):
        self.assertEqual(review.validate(self.state),[])
        report=review.render(self.state)
        self.assertIn('[模拟标准 非真实依据 TEST-2026](<https://example.org/standard>)',report)
        self.assertIn('[标准全文](<https://example.org/standard.pdf>)',report)
        self.assertIn('核验日期 2026-11-03',report)
        self.assertFalse((self.root/'catalog.sqlite').exists())

    def test_online_rejections(self):
        cases=[('全文未读',lambda s:s['verification_log'][0].update(fulltext_status='metadata_only')),
               ('未核对条款',lambda s:s['verification_log'][0].update(reviewed_clauses=[])),
               ('错版本',lambda s:s['verification_log'][0].update(version='2025')),
               ('错URL',lambda s:s['verification_log'][0].update(url='https://example.org/other')),
               ('没有公告',lambda s:s['verification_log'][0].update(status_url='')),
               ('身份未知',lambda s:s['verification_log'][0].update(source_authority='unknown')),
               ('过期核验',lambda s:s['verification_log'][0].update(accessed_on='2025-01-01')),
               ('未来核验',lambda s:s['verification_log'][0].update(accessed_on='2027-01-01')),
               ('未实施',lambda s:s['checks'][0]['basis'].update(effective_on='2027-01-01')),
               ('已失效',lambda s:s['checks'][0]['basis'].update(expires_on='2026-11-01')),
               ('坏链接',lambda s:s['checks'][0]['basis'].update(url='javascript:alert(1)')),
               ('网络失败',lambda s:s['verification_log'][0].update(failure='timeout')),
               ('适用未知',lambda s:s['checks'][0]['applicability']['scope'].update(result='unknown')),
               ('推荐判违规',lambda s:s['checks'][0]['basis'].update(force='recommended')),
               ('重复核验ID',lambda s:s['verification_log'].append(copy.deepcopy(s['verification_log'][0])))]
        for name,mutate in cases:
            with self.subTest(name=name):
                s=copy.deepcopy(self.state);mutate(s)
                self.assertTrue(review.validate(s))
                with self.assertRaises(ValueError):review.render(s)

    def test_conforming_has_clickable_basis(self):
        self.check['result']='conforming'
        self.assertIn('[模拟标准 非真实依据 TEST-2026]',review.render(self.state))

    def test_insufficient_still_reports(self):
        self.check.update(result='insufficient',basis=None)
        self.assertEqual(review.validate(self.state),[])
        self.assertIn('资料/依据不足',review.render(self.state))

    def test_old_local_records_still_checked(self):
        root=self.root/'kb'; kb.init(root)
        raw=b'synthetic local source'; sha=kb.digest(raw); (root/'originals'/sha).write_bytes(raw)
        meta={'title':'模拟本地标准','layer':'B','version':'2026','region':'全国','topics':['测试'],'status':'effective','kind':'standard','official_url':'https://example.org/standard','issuer':'测试机关','effective_on':'2026-01-01','verified_on':'2026-11-03','verification_note':'模拟核验'}
        conn=sqlite3.connect(root/'catalog.sqlite');conn.execute('INSERT INTO records VALUES(?,?,?,?,?)',('local1',1,json.dumps(meta),sha,'synthetic'));conn.commit();conn.close()
        self.b.update(source_type='local',record_id='local1',revision=1,sha256=sha)
        self.log['record_id']='local1'
        self.assertEqual(review.validate(self.state,root),[])
        (root/'originals'/sha).write_bytes(b'changed')
        self.assertTrue(any('哈希' in x for x in review.validate(self.state,root)))

if __name__=='__main__':unittest.main(verbosity=2)
