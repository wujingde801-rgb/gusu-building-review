"""Validate and render recorded location/procedure research; no automatic GIS inference."""
import datetime as dt
from urllib.parse import urlsplit

def web(value):
    try: return isinstance(value,str) and urlsplit(value).scheme in {'https','http'} and bool(urlsplit(value).hostname)
    except ValueError: return False

def validate(context, date):
    if context is None: return []  # Legacy reports remain readable with unperformed notice.
    errors=[]
    if context.get('status') not in {'pending','partial','reviewed'}: errors.append('区位核查状态无效')
    identities=context.get('designations',[])+context.get('zones',[])
    known={x.get('id'):x for x in identities}
    actions={x.get('id'):x for x in context.get('actions',[])}
    if len(known)!=len(identities) or None in known: errors.append('区位身份/范围ID缺失或重复')
    if len(actions)!=len(context.get('actions',[])) or None in actions: errors.append('改造行为ID缺失或重复')
    for x in identities:
        if x.get('relation') not in {'confirmed','inside','outside','overlap','candidate','unknown'}: errors.append('身份/范围关系无效')
        if x.get('relation') in {'confirmed','inside','outside','overlap'} and (not web(x.get('source_url')) or not x.get('locator') or not x.get('match_reason')): errors.append('确定身份/范围关系缺少官方出处、位置或匹配理由')
    for x in context.get('procedures',[]):
        if x.get('status') not in {'confirmed','candidate','unknown','not_applicable'}: errors.append('报批核查状态无效')
        if x.get('status') not in {'confirmed','not_applicable'}: continue
        if not x.get('action_ids') or any(i not in actions for i in x.get('action_ids',[])): errors.append('报批结论未关联实际改造行为')
        refs=x.get('trigger_ids',[])
        if not refs or any(i not in known or known[i].get('relation') in {'unknown','candidate'} for i in refs): errors.append('报批结论依赖的保护身份/范围未确认')
        if not all(x.get(k) for k in ('name','trigger_reason','clause','authority','authority_role','guide_locator')) or not web(x.get('basis_url')) or not web(x.get('guide_url')): errors.append('报批结论缺少条款、部门角色或现行办事指南')
        try:
            delta=(dt.date.fromisoformat(date)-dt.date.fromisoformat(x['checked_on'])).days
            if not 0<=delta<=90: errors.append('报批核验日期过期/无效')
        except (KeyError,TypeError,ValueError): errors.append('报批核验日期缺失/无效')
    if context.get('status')=='reviewed' and (context.get('unresolved') or not context.get('search_log')): errors.append('区位核查不能在缺少查询记录或存在未核实项时标为已核查')
    return errors

def render(context,link):
    if not context: return ['## 区位保护与报批核查','','旧记录未执行此项；不得据此认定无保护或报批要求。','']
    lines=['## 区位保护与报批核查','', '核查状态：'+str(context.get('status'))+'；已确认程序仅指资料匹配，不代表获批。','', '位置：'+str(context.get('location',{}).get('raw_address') or '待定位'),'']
    for kind in ('designations','zones'):
        for x in context.get(kind,[]):
            lines += ['- '+str(x.get('name','待核实'))+'：'+str(x.get('relation'))+'；'+str(x.get('match_reason','待核实'))+'；'+(link('官方出处',x.get('source_url')) or '未取得官方出处')+'；位置 '+str(x.get('locator','待核实'))]
    for x in context.get('procedures',[]):
        lines += ['', '### '+str(x.get('name','待核实事项'))+'（'+str(x.get('status'))+'）', '触发条件：'+str(x.get('trigger_reason','待核实')), '部门与角色：'+str(x.get('authority','待核实'))+' / '+str(x.get('authority_role','待核实')), '依据：'+(link(str(x.get('clause') or '条款'),x.get('basis_url')) or '待核实')+'；'+(link('办事指南',x.get('guide_url')) or '受理层级与指南待核实'), '材料/顺序：'+str(x.get('materials_sequence','待核实'))]
    lines += ['', '区位与报批待核实：'+('；'.join(context.get('unresolved',[])) or '无已记录待核实项'),'']
    return lines
