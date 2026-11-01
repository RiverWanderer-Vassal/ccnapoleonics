import xml.etree.ElementTree as ET
def next_token(s, i, d):
    """VASSAL SequenceEncoder.Decoder: a delimiter preceded by backslash is escaped (backslash dropped)."""
    out=[]; n=len(s); j=i
    while j<n:
        c=s[j]
        if c==d:
            if out and out[-1]=='\\':
                out[-1]=d; j+=1; continue
            tok=''.join(out)
            return unq(tok), j+1
        out.append(c); j+=1
    return unq(''.join(out)), None
def unq(t):
    if len(t)>=2 and t[0]=="'" and t[-1]=="'": return t[1:-1]
    return t
def split_all(s,d):
    res=[];i=0
    while True:
        t,i=next_token(s,i,d); res.append(t)
        if i is None: return res
def traits(typestr):
    out=[]; s=typestr
    while True:
        t,i=next_token(s,0,'\t'); out.append(t)
        if i is None: return out
        s,_=next_token(s,i,'\t')
def piece_traits(text):
    if not text: return []
    parts=split_all(text,'/')
    if len(parts)>=3 and parts[0]=='+': return traits(parts[2])
    return traits(text)
def load(path): return ET.parse(path).getroot()

import re as _re
def build_protos(r):
    return {p.get('name'):piece_traits(p.text) for p in r.iter('VASSAL.build.module.PrototypeDefinition')}
def expand(trs, protos, seen=None, path=()):
    """Expand prototype traits; returns list of (trait, source-proto-path)"""
    out=[]
    for t in trs:
        if t.startswith('prototype;'):
            name=t.split(';',1)[1]
            if name in path: out.append(('RECURSIVE '+name,path)); continue
            if name not in protos: out.append(('MISSINGPROTO;'+name,path)); continue
            out+=expand(protos[name],protos,seen,path+(name,))
        else: out.append((t,path))
    return out
def ttype(t): return t.split(';',1)[0]

def _esc(s,d):
    return s.replace(d,'\\'+d)
def _app(buf,s,d,first):
    out=buf if first else buf+d
    if s is None or s=='': return out
    if s[0]=='\\' or (s[0]=="'" and s[-1]=="'"): return out+"'"+_esc(s,d)+"'"
    return out+_esc(s,d)
def encode_chain(items):
    """items outermost-first list of strings -> nested tab encoding like Decorator.getType/getState"""
    inner=items[-1]
    for t in reversed(items[:-1]):
        inner=_app(_app('',t,'\t',True),inner,'\t',False)
    return inner

def encode_seq(items, d):
    out=''
    for i,s in enumerate(items):
        out=_app(out,s,d,i==0)
    return out
def proto_parts(text):
    parts=split_all(text,'/')
    assert parts[0]=='+' , parts[:2]
    return parts  # ['+', id, type, state]
def proto_lists(text):
    p=proto_parts(text); return p, traits(p[2]), traits(p[3])
def proto_text(p, T, S):
    q=list(p); q[2]=encode_chain(T); q[3]=encode_chain(S)
    return encode_seq(q,'/')
