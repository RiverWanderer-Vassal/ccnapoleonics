import sys, zipfile, shutil, os
sys.path.insert(0,'/home/claude/tools')
from vdec import *
def xesc(s):
    return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
class Build:
    def __init__(self, path):
        self.raw=open(path,encoding='utf-8').read(); self.root=ET.fromstring(self.raw.encode('utf-8'))
        self.log=[]
    def proto(self, name):
        for p in self.root.iter('VASSAL.build.module.PrototypeDefinition'):
            if p.get('name')==name: return p
        raise KeyError(name)
    def edit_proto(self, name, fn, note):
        p=self.proto(name); old=p.text
        parts,T,S=proto_lists(old)
        T2,S2=fn(list(T),list(S))
        new=proto_text(parts,T2,S2)
        eo=xesc(old)
        n=self.raw.count(eo)
        if n!=1: raise RuntimeError(f'{name}: original text found {n} times')
        self.raw=self.raw.replace(eo,xesc(new)); p.text=new
        self.log.append(f'{name}: {note}')
    def replace_raw(self, old, new, note, count=1):
        n=self.raw.count(old)
        if n!=count: raise RuntimeError(f'{note}: found {n} times, expected {count}')
        self.raw=self.raw.replace(old,new); self.log.append(note)
    def save(self, path): open(path,'w',encoding='utf-8').write(self.raw)
def build_vmod(src_vmod, buildfile_path, out_vmod, version=None):
    zin=zipfile.ZipFile(src_vmod); zout=zipfile.ZipFile(out_vmod,'w',zipfile.ZIP_DEFLATED)
    for it in zin.infolist():
        data=zin.read(it.filename)
        if it.filename=='buildFile.xml': data=open(buildfile_path,'rb').read()
        if version and it.filename in ('buildFile.xml','moduledata'):
            s=data.decode('utf-8'); import re
            if it.filename=='moduledata': s=re.sub(r'<version>[^<]*</version>','<version>'+version+'</version>',s,1)
            else: s=re.sub(r'(<VASSAL.build.GameModule [^>]*?version=")[^"]*(")',r'\g<1>'+version+r'\2',s,1)
            data=s.encode('utf-8')
        zout.writestr(it, data)
    zout.close()
def idx(T, startswith):
    r=[i for i,t in enumerate(T) if t.startswith(startswith)]
    if len(r)!=1: raise RuntimeError(f'{startswith}: {len(r)} matches')
    return r[0]

def set_field(trait, i, value):
    f=split_all(trait,';')
    while len(f)<=i: f.append('')
    f[i]=value
    return encode_seq(f,';')
