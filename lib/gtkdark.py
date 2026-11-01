import re,sys
MAP={'#333333':'#141414','#242424':'#0d0d0d','#373737':'#1a1a1a','#2e2e2e':'#181818','#0860f2':'#0091ff','#2e7cf7':'#2aa5ff','#dedede':'#f5f5f5','#dadada':'#f5f5f5'}
def hexfix(m):
    h='#'+m.group(1).lower()
    if h in MAP: return MAP[h]
    r,g,b=int(h[1:3],16),int(h[3:5],16),int(h[5:7],16)
    if r==g==b and 0x14<=r<=0x50: v=round(r*0.5); return '#%02x%02x%02x'%(v,v,v)
    return m.group(0)
def rgbafix(m):
    r,g,b=int(m.group(2)),int(m.group(3)),int(m.group(4))
    if (r,g,b)==(51,51,51): return '%s(20, 20, 20%s'%(m.group(1),m.group(5))
    if (r,g,b)==(36,36,36): return '%s(13, 13, 13%s'%(m.group(1),m.group(5))
    if r==g==b and 0x14<=r<=0x50: v=round(r*0.5); return '%s(%d, %d, %d%s'%(m.group(1),v,v,v,m.group(5))
    if (r,g,b)==(8,96,242): return '%s(0, 145, 255%s'%(m.group(1),m.group(5))
    return m.group(0)
for f in sys.argv[1:]:
    t=open(f,encoding='utf-8').read()
    t=re.sub(r'#([0-9a-fA-F]{6})\b',hexfix,t)
    t=re.sub(r'(rgba?)\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(\s*[,)])',rgbafix,t)
    open(f,'w',encoding='utf-8').write(t)
