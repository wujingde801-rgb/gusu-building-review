#!/usr/bin/env python3
"""Project routing, atomic coverage, evidence validation and human-review Markdown."""
import argparse
import datetime as dt
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit, quote
import kb

ASSETS=Path(__file__).resolve().parents[1]/'assets'
CHECK_RESULTS={'pending','conforming','violation','not_applicable','insufficient','contradiction','optimization'}

def read(path): return json.loads(Path(path).read_text('utf-8'))
def write(path,x): Path(path).write_text(kb.dump(x)+'\n',encoding='utf-8')
def hashfile(p): return kb.digest(Path(p).read_bytes())

def route(profile,mode='detailed',specialty=None):
    if mode not in {'quick','detailed','specialty'}: raise ValueError('非法审查模式')
    if mode=='specialty' and not specialty: raise ValueError('专项复核须选择专项')
    modules=read(ASSETS/'modules.json')
    selected=[]
    for m in modules:
        trigger=m['trigger']
        value=True if trigger=='always' else profile.get(trigger)
        if value is False: continue
        if mode=='specialty' and m['id'] not in {'identity','consistency',specialty}: continue
        focus={'concept':'功能、场地、保护策略与重大风险','planning':'总图、指标、风貌与主要功能组织','preliminary':'专业接口、技术策略与性能论证','construction':'尺寸、材料、工艺和跨图一致性'}.get(profile.get('stage'),'阶段未知：仅观察事实，待核实设计深度')
        selected.append({**m,'stage_focus':focus,'routing':'active' if value is True else 'candidate','reason':trigger if value is not None else trigger+':unknown'})
    if specialty and specialty not in {m['id'] for m in modules}: raise ValueError('未知专项')
    return selected

def load_rules(kroot):
    if not kroot: return []
    result=[]
    for row in kb.records(kroot,all_status=True):
        m=row['metadata']
        if m.get('kind')!='rule' or m.get('status')!='effective': continue
        original=Path(kroot)/'originals'/row['blob']
        if not original.is_file() or hashfile(original)!=row['blob']: raise ValueError('规则原文缺失或哈希变化')
        rule=json.loads(row['text'])
        if rule.get('status')!='active': continue
        if not rule.get('rule_id') or not rule.get('obligations') or not rule.get('applicability'):
            raise ValueError('规则缺少ID、义务或适用条件')
        if not all(o.get('id') and o.get('question') for o in rule['obligations']):
            raise ValueError('规则义务格式无效')
        result.append({'record_id':row['id'],'revision':row['revision'],'sha256':row['blob'],'rule':rule})
    return result

def start(pdf,folder,profile,mode,specialty=None,kroot=None):
    from pypdf import PdfReader
    folder=Path(folder).resolve()
    if folder.exists(): raise ValueError('项目目录已存在；为避免覆盖请使用新目录')
    pdf=Path(pdf).resolve(); reader=PdfReader(str(pdf))
    if reader.is_encrypted: raise ValueError('加密PDF需提供可读副本')
    modules=route(profile,mode,specialty)
    folder.mkdir(parents=True)
    checks=[]
    for m in modules:
        for i,prompt in enumerate(m['checks'],1):
            checks.append({'id':m['id']+'-'+str(i).zfill(2),'module':m['id'],'question':prompt,'canonical_question':prompt,
                           'routing':m['routing'],'result':'pending','fact_ids':[],
                           'applicability':{k:{'result':'unknown','reason':''} for k in ('identity','date','region','project_type','stage','scope','exceptions','conflicts')},
                           'basis':None,'comparison':'','counterevidence':{'searched':[],'result':'unknown','reason':''},
                           'risk':'unassessed','action':'','human':{'status':'pending','note':''}})
    rule_snapshot=load_rules(kroot)
    for entry in rule_snapshot:
        rule=entry['rule']
        for o in rule['obligations']:
            checks.append({'id':'rule:'+rule['rule_id']+':'+o['id'],'module':'local-rule',
                           'question':o['question'],'canonical_question':o['question'],'routing':'candidate','result':'pending','fact_ids':[],
                           'applicability':{k:{'result':'unknown','reason':''} for k in ('identity','date','region','project_type','stage','scope','exceptions','conflicts')},
                           'basis':dict(rule.get('basis') or {}),'comparison':'','counterevidence':{'searched':[],'result':'unknown','reason':''},
                           'risk':'unassessed','action':'','human':{'status':'pending','note':''}})
    if len({c['id'] for c in checks})!=len(checks): raise ValueError('规则/义务ID重复')
    inventory=[]
    for i,page in enumerate(reader.pages,1):
        try: text=page.extract_text() or ''; error=None
        except Exception as exc: text=''; error=type(exc).__name__
        inventory.append({'page':i,'printed_page':None,'drawing_id':None,'title':None,'visual_status':'unseen',
                          'text_status':'available' if text.strip() else 'scan_or_unreadable','extract_error':error,'text_excerpt':text[:3000]})
    state={'schema_version':1,'date':dt.date.today().isoformat(),'mode':mode,'specialty':specialty,
           'source':{'path':str(pdf),'sha256':hashfile(pdf),'pages':len(reader.pages)},'profile':profile,
           'route':modules,'rules_snapshot':rule_snapshot,'inventory':inventory,'facts':[],'evidence':[],'checks':checks,
           'knowledge_layers':{k:{'status':'unavailable','sources':[],'use':''} for k in 'ABCD'},
           'verification_log':[],'human_review':{'status':'pending','note':''}}
    write(folder/'review.json',state)
    return {'workspace':str(folder),'pages':len(inventory),'atomic_checks':len(checks),'route':[m['id'] for m in modules]}

def validate(state,kroot=None):
    errors=[]
    def fail(msg): errors.append(msg)
    if state.get('schema_version') != 1: return ['不支持的schema']
    source=state.get('source',{})
    if not Path(source.get('path','')).is_file() or hashfile(source['path'])!=source.get('sha256'): fail('项目PDF缺失或发生变化')
    pages=source.get('pages',0)
    inventory=state.get('inventory',[])
    if sorted(p.get('page',0) for p in inventory)!=list(range(1,pages+1)): fail('PDF页码清单不完整/重复')
    for p in inventory:
        if p.get('visual_status') not in {'unseen','seen','unreadable'}: fail('非法页面阅读状态')
    evidence={}
    for e in state.get('evidence',[]):
        if not e.get('id') or e['id'] in evidence: fail('证据ID为空/重复')
        evidence[e.get('id')]=e
        box=e.get('bbox',[])
        if e.get('source_sha256')!=source.get('sha256') or e.get('page',0) not in range(1,pages+1): fail('证据源或页码无效')
        if len(box)!=4 or not all(isinstance(v,(int,float)) and 0<=v<=1 for v in box) or (len(box)==4 and (box[0]>=box[2] or box[1]>=box[3])): fail('证据bbox必须为0..1归一化矩形')
        path=Path(e.get('path',''))
        if not path.is_file() or hashfile(path)!=e.get('sha256'): fail('证据图缺失或修改')
        if not e.get('observation') or e.get('quality') not in {'clear','unclear'}: fail('证据需观察记录和清晰度')
    facts={}
    for f in state.get('facts',[]):
        if not f.get('id') or f['id'] in facts: fail('事实ID为空/重复')
        facts[f.get('id')]=f
        if not f.get('observation') or not f.get('evidence_ids') or any(x not in evidence for x in f.get('evidence_ids',[])): fail('事实必须指向已登记图文证据')
    log_ids=[v.get('id') for v in state.get('verification_log',[])]
    if any(not x for x in log_ids) or len(log_ids)!=len(set(log_ids)): fail('依据核验记录ID为空/重复')
    ids=set()
    expected_questions={m['id']+'-'+str(i).zfill(2):(m['id'],q) for m in route(state['profile'],state['mode'],state.get('specialty')) for i,q in enumerate(m['checks'],1)}
    expected={m['id']+'-'+str(i).zfill(2) for m in route(state['profile'],state['mode'],state.get('specialty')) for i,_ in enumerate(m['checks'],1)}
    current_rules=load_rules(kroot)
    if state.get('rules_snapshot',[])!=current_rules: fail('规则库版本已变更或未提供原知识库')
    for entry in state.get('rules_snapshot',[]):
        for obligation in entry['rule']['obligations']:
            rid='rule:'+entry['rule']['rule_id']+':'+obligation['id']
            expected.add(rid)
            expected_questions[rid]=('local-rule',obligation['question'])
    actual={c.get('id') for c in state.get('checks',[])}
    if actual != expected: fail('原子检查被删改或路由已变更，需重新展开并保留历史')
    db={r['id']:r for r in kb.records(kroot,all_status=True,as_of=state['date'])} if kroot else {}
    for c in state.get('checks',[]):
        cid=c.get('id'); prefix=str(cid)+': '
        if cid in ids: fail(prefix+'重复检查ID')
        ids.add(cid)
        if (c.get('module'),c.get('canonical_question')) != expected_questions.get(cid): fail(prefix+'原子检查模块/原始义务被改写')
        result=c.get('result')
        if result not in CHECK_RESULTS: fail(prefix+'非法结论'); continue
        if result=='pending': continue
        if not c.get('action') or not c.get('comparison'): fail(prefix+'缺少比较理由或后续动作')
        if result=='insufficient': continue
        if result=='optimization':
            if not c.get('fact_ids') or any(x not in facts for x in c['fact_ids']): fail(prefix+'优化建议需项目事实')
            continue
        fs=[facts.get(x) for x in c.get('fact_ids',[])]
        if not fs or any(f is None for f in fs): fail(prefix+'缺少可追溯项目事实'); continue
        es=[evidence[e] for f in fs for e in f.get('evidence_ids',[]) if e in evidence]
        if any(next((p['visual_status'] for p in inventory if p['page']==e['page']), 'unseen')!='seen' for e in es): fail(prefix+'引用页面尚未视觉核验')
        if not es or any(e.get('quality')!='clear' for e in es): fail(prefix+'图文证据不清晰')
        if result=='not_applicable':
            if not c.get('scope_exclusion_reason'): fail(prefix+'不适用需正向范围证据及理由')
            continue
        if result=='contradiction':
            if len({e['id'] for e in es})<2: fail(prefix+'图文矛盾需两处证据')
            continue
        gates=c.get('applicability',{})
        required={'identity','date','region','project_type','stage','scope','exceptions','conflicts'}
        if set(gates)!=required or any(g.get('result')!='pass' or not g.get('reason') for g in gates.values()): fail(prefix+'适用性/冲突关卡未关闭')
        if state['profile'].get('stage') not in {'concept','planning','preliminary','construction'} or state['profile'].get('protection_identity') not in {'cultural_relic_protected','immovable_relic','historic_building','traditional_character','ordinary_in_protected_area','ordinary','mixed'}: fail(prefix+'项目设计阶段/保护身份未知')
        counter=c.get('counterevidence',{})
        if counter.get('result') not in {'consistent','none_found'} or not counter.get('reason') or not counter.get('searched') or any(e not in evidence for e in counter.get('searched',[])): fail(prefix+'反证检索未完成')
        b=c.get('basis') or {}
        if not all(b.get(k) for k in ('clause','excerpt','source_locator','force','verification_id')):
            fail(prefix+'条文、定位、措辞属性或官方核验记录缺失')
        if b.get('force') not in {'mandatory','recommended','informative'}:
            fail(prefix+'依据措辞属性无效')
        log=next((x for x in state.get('verification_log',[]) if x.get('id')==b.get('verification_id')),None)
        if b.get('source_type','local') == 'online':
            for message in validate_online_basis(b,log,state['date']): fail(prefix+message)
        elif b.get('source_type','local') == 'local':
            r=db.get(b.get('record_id'))
            if not r or not r['basis_usable']: fail(prefix+'缺少有效B类正式依据'); continue
            if b.get('revision')!=r['revision'] or b.get('sha256')!=r['blob']: fail(prefix+'依据版本已变化')
            if not (Path(kroot)/'originals'/r['blob']).is_file() or hashfile(Path(kroot)/'originals'/r['blob']) != r['blob']: fail(prefix+'规范原文哈希变化')
            if not log or log.get('record_id')!=r['id'] or not all(log.get(k) for k in ('url','accessed_on','status_evidence','fulltext_locator')): fail(prefix+'官方核验链不完整')
            if log and log.get('url')!=r['metadata'].get('official_url'): fail(prefix+'官方核验URL与入库正式来源不一致，需补充确认后的元数据')
        else:
            fail(prefix+'未知依据来源类型')
        if log:
            try:
                delta=(dt.date.fromisoformat(state['date'])-dt.date.fromisoformat(log['accessed_on'])).days
                if not 0<=delta<=90: fail(prefix+'官方核验已过期/日期无效')
            except (ValueError,KeyError,TypeError): fail(prefix+'官方核验日期无效')
        if result=='violation' and b.get('force')!='mandatory': fail(prefix+'推荐性要求不能输出明确不符合')
    return errors

def valid_web_url(url):
    if not isinstance(url,str) or not url.strip(): return False
    try:
        parts=urlsplit(url)
        return parts.scheme in {'http','https'} and bool(parts.hostname) and not parts.username and not parts.password
    except ValueError: return False

def validate_online_basis(b,log,review_date):
    """Check recorded online verification, not network availability or professional truth."""
    errors=[]
    required=('title','standard_code','version','issuer','url','effective_on')
    if not all(isinstance(b.get(k),str) and b[k].strip() for k in required):
        errors.append('线上依据缺少名称、编号、版本、发布机关、链接或实施日期')
    if not valid_web_url(b.get('url')): errors.append('线上依据需可点击的HTTP(S)正式来源链接')
    if b.get('status')!='effective': errors.append('线上依据现行有效性未核实')
    try:
        when=dt.date.fromisoformat(review_date)
        if dt.date.fromisoformat(b['effective_on'])>when: errors.append('线上依据尚未实施')
        if b.get('expires_on') and dt.date.fromisoformat(b['expires_on'])<=when: errors.append('线上依据已失效')
    except (ValueError,KeyError,TypeError): errors.append('线上依据实施/失效日期无效')
    if not isinstance(log,dict): return errors+['线上依据缺少对应核验记录']
    if any(log.get(k)!=b.get(k) for k in ('title','standard_code','version','url')):
        errors.append('线上依据与核验记录的名称、编号、版本或URL不一致')
    if log.get('source_authority') not in {'official','authorized_publication'} or not log.get('authority_note'):
        errors.append('线上来源发布身份未核实')
    if log.get('status_checked') is not True or not valid_web_url(log.get('status_url')) or not log.get('status_evidence'):
        errors.append('缺少实施/修改/替代/废止核验结果及公告链接')
    if not valid_web_url(log.get('fulltext_url')) or log.get('fulltext_status')!='read' or not log.get('fulltext_locator'):
        errors.append('未实际读取正式全文或缺少全文链接/定位')
    clauses=log.get('reviewed_clauses',[])
    if not isinstance(clauses,list) or not any(isinstance(x,dict) and x.get('clause')==b.get('clause') and x.get('source_locator')==b.get('source_locator') and x.get('observation') for x in clauses):
        errors.append('引用条款缺少对应的实际阅读位置和观察记录')
    if log.get('failure'): errors.append('线上核验仍有未解决失败事项')
    return errors

def source_link(label, url):
    """Render an actual recorded HTTP(S) source as a clickable Markdown link."""
    if not isinstance(url,str) or not url.strip(): return None
    url=url.strip()
    try:
        parts=urlsplit(url)
        if parts.scheme not in {'http','https'} or not parts.netloc: return None
    except ValueError: return None
    label=str(label).replace('\\','\\\\').replace('[','\\[').replace(']','\\]').replace('\n',' ')
    target=quote(url,safe=":/?#[]@!$&'()*+,;=%")
    return '['+label+'](<'+target+'>)'

def render(state,kroot=None):
    errors=validate(state,kroot)
    if errors: raise ValueError('报告校验失败:\n'+'\n'.join(errors))
    counts={r:sum(c['result']==r for c in state['checks']) for r in sorted(CHECK_RESULTS)}
    unseen=[p['page'] for p in state['inventory'] if p['visual_status']!='seen']
    lines=['# 【AI辅助审查·待人工复核】'+state['profile'].get('name','未命名项目'),'','日期：'+state['date'],
           '模式：'+state['mode']+'；设计阶段：'+str(state['profile'].get('stage')),
           '源PDF SHA-256：`'+state['source']['sha256']+'`','',
           '本报告供人工复核，不代替法定审查、专业鉴定或主管部门审批。',
           '覆盖状态：'+('部分审查' if unseen or counts['pending'] or counts['insufficient'] else '已记录范围内检查完成，仍待人工复核'),
           '未完成视觉核验页：'+str(unseen),'检查统计：明确不符合 '+str(counts['violation'])+'；图文矛盾 '+str(counts['contradiction'])+'；建议优化 '+str(counts['optimization'])+'；资料/依据不足 '+str(counts['insufficient'])+'；尚未审查 '+str(counts['pending'])+'；已核对 '+str(counts['conforming'])+'；不适用 '+str(counts['not_applicable']),'',
           '## 项目身份、范围与适用性','',kb.dump(state['profile']),'',
           '## 审查意见与待核实事项','']
    labels={'violation':'明确不符合（依据已校验，待人工复核）','insufficient':'资料/依据不足','contradiction':'图文矛盾','optimization':'建议优化','pending':'尚未审查','not_applicable':'不适用','conforming':'已核对项'}
    source_rows={r['id']:r for r in kb.records(kroot,all_status=True)} if kroot else {}
    for c in state['checks']:
        if c['result'] in {'not_applicable','pending'}: continue
        b=c.get('basis') or {}; record=source_rows.get(b.get('record_id')) if b.get('source_type','local')=='local' else None
        source_display='未取得可引用的正式依据'
        if record:
            meta=record['metadata']
            linked=source_link(meta['title'],meta.get('official_url'))
            source_display=(linked or meta['title']+'（缺少可用的在线来源链接）')+'；版本 '+meta['version']
        elif b:
            log=next((v for v in state.get('verification_log',[]) if v.get('id')==b.get('verification_id')),{})
            linked=source_link(' '.join(str(b.get(k) or '') for k in ('title','standard_code')).strip() or '线上依据来源（适用性待核实）',log.get('url'))
            if linked: source_display=linked+'；版本 '+str(b.get('version','待核实'))
        log=next((v for v in state.get('verification_log',[]) if v.get('id')==b.get('verification_id')),{})
        fulltext=source_link('标准全文',log.get('fulltext_url'))
        if fulltext: source_display+='；'+fulltext
        if log.get('accessed_on'): source_display+='；核验日期 '+str(log['accessed_on'])
        basis_display=('条文 '+str(b.get('clause','待核实'))+'；原文措辞：'+str(b.get('excerpt','待取得'))+'；原文定位：'+str(b.get('source_locator','待核实'))) if b else '未取得正式依据，不能据此作强制性合规结论'
        lines += ['### '+c['id']+' '+labels[c['result']],c['question'],'',
                  '风险：'+c.get('risk','unassessed'), '观察及比较：'+(c.get('comparison') or '尚未完成'),
                  '修改/补充建议：'+(c.get('action') or '完成此项检查'),
                  '事实引用：'+', '.join(c.get('fact_ids',[])),
                  '依据名称与版本：'+source_display, '依据与条文：'+basis_display,
                  '人工复核：'+('待复核' if c.get('human',{}).get('status','pending')=='pending' else c['human']['status'])+' '+c.get('human',{}).get('note',''),'']
    lines += ['## 覆盖矩阵','', '| 检查ID | 检查事项 | 状态 |','|---|---|---|']
    for c in state['checks']: lines += ['| '+c['id']+' | '+c['question'].replace('|','/')+' | '+labels[c['result']]+' |']
    lines += ['', '## 项目事实索引','', kb.dump(state['facts']), '', '## 图文证据索引','']
    for e in state['evidence']:
        lines += [e['id']+'：PDF第'+str(e['page'])+'页；bbox '+str(e['bbox'])+'；'+e['observation'],
                  '!['+e['id']+']('+e['path']+')','']
    lines += ['## 依据来源链接','']
    for log in state.get('verification_log',[]):
        linked=source_link(log.get('title') or log.get('id','依据来源'),log.get('url'))
        fulltext=source_link('标准全文',log.get('fulltext_url'))
        status_link=source_link('实施/修订公告',log.get('status_url'))
        lines += ['- '+(linked or '未取得可用的在线来源链接')+('；'+fulltext if fulltext else '')+('；'+status_link if status_link else '')+'；核验日期：'+str(log.get('accessed_on','未记录'))]
    lines += ['', '## 依据核验与知识层使用','',kb.dump(state['verification_log']),kb.dump(state['knowledge_layers']),
              '', '## 人工复核记录','',kb.dump(state['human_review'])]
    return '\n'.join(lines)+'\n'

def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='cmd',required=True)
    s=sub.add_parser('init'); s.add_argument('--pdf',required=True); s.add_argument('--workspace',required=True); s.add_argument('--profile',required=True); s.add_argument('--mode',default='detailed',choices=['quick','detailed','specialty']); s.add_argument('--specialty'); s.add_argument('--kb')
    for command in ('validate','report'):
        s=sub.add_parser(command); s.add_argument('state'); s.add_argument('--kb');
        if command=='report': s.add_argument('--output',required=True)
    a=p.parse_args()
    if a.cmd=='init': print(kb.dump(start(a.pdf,a.workspace,read(a.profile),a.mode,a.specialty,a.kb)))
    else:
        state=read(a.state)
        if a.cmd=='validate':
            errors=validate(state,a.kb); print(kb.dump({'valid':not errors,'errors':errors})); sys.exit(bool(errors))
        else:
            output=Path(a.output)
            if output.exists(): raise ValueError('输出已存在，请用新文件名保留旧报告')
            output.write_text(render(state,a.kb),encoding='utf-8'); print(str(output.resolve()))

if __name__=='__main__':
    try: main()
    except (ValueError, OSError, KeyError, TypeError) as e:
        print(str(e),file=sys.stderr); sys.exit(2)
