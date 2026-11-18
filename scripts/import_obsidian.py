#!/usr/bin/env python3
"""Read selected, approved public notes from the Obsidian vault."""
from __future__ import annotations
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VAULT = ROOT / "AslıOlanDüzenObsidianVault"
MONTHS = {"ocak":1,"şubat":2,"subat":2,"mart":3,"nisan":4,"mayıs":5,"mayis":5,"haziran":6,"temmuz":7,"ağustos":8,"agustos":8,"eylül":9,"eylul":9,"ekim":10,"kasım":11,"kasim":11,"aralık":12,"aralik":12}
WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]+))?\]\]")

def slug(text):
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.casefold().replace("ı", "i")
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "record"

def normalize(text):
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.casefold().replace("ı", "i")
    text = re.sub(r"\.(md|txt)$", "", text, flags=re.I)
    text = text.replace("\\", "/").split("/")[-1]
    text = re.sub(r"[_-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def read_doc(relative):
    path = VAULT / relative
    if not path.is_file() or path.suffix.lower() not in {".md", ".txt"}:
        return None
    raw = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    meta = {}
    if raw.startswith("---\n"):
        end = raw.find("\n---", 4)
        if end >= 0:
            for line in raw[4:end].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip().lower()] = v.strip().strip("'\"")
            raw = raw[end + 4:].lstrip("\n")
    status = meta.get("status", "").casefold()
    tags = meta.get("tags", "").casefold()
    privacy = meta.get("gizlilik", meta.get("privacy", "")).casefold()
    blocked = ("draft", "proposed", "taslak", "yazar onayı bekliyor", "approval pending", "gizli", "classified")
    if any(term in status + " " + tags + " " + privacy for term in blocked):
        return None
    lines = raw.splitlines()
    title = meta.get("title", "")
    if not title:
        for i, line in enumerate(lines):
            m = re.match(r"^#\s+(.+)$", line.strip())
            if m:
                title = m.group(1).strip()
                lines.pop(i)
                break
    if not title:
        title = path.stem
    content = "\n".join(lines).strip()
    summary = meta.get("summary", "")
    if not summary:
        for para in re.split(r"\n\s*\n", content):
            p = para.strip()
            if p and not p.startswith(("> [!", "%%", "|")):
                summary = re.sub(r"[*_>#]", "", p)[:250]
                break
    aliases = []
    raw_aliases = meta.get("aliases", "")
    if raw_aliases.startswith("[") and raw_aliases.endswith("]"):
        aliases = [x.strip().strip("'\"") for x in raw_aliases[1:-1].split(",")]
    return {"title":title,"summary":summary,"content":content,"aliases":aliases,"sourceName":path.stem,"path":relative.replace("\\","/")}

def node(category, doc, date=""):
    return {"id":category+"-"+slug(doc["path"]),"path":doc["path"],"sourceName":doc["sourceName"],"title":doc["title"],"date":date,"summary":doc["summary"],"content":doc["content"],"order":999,"aliases":doc["aliases"],"children":[],"links":[]}

def group(category,title,date,summary,children,key):
    return {"id":category+"-"+slug(key),"path":key,"sourceName":title,"title":title,"date":date,"summary":summary,"content":summary,"order":0,"aliases":[],"children":children,"links":[]}

def parse_event_date(filename,title):
    text=(filename+" "+title).casefold()
    ys=re.findall(r"\b(19\d{2}|20\d{2})\b",text)
    year=int(ys[0]) if ys else None
    month=day=0
    names=sorted(MONTHS.keys(),key=len,reverse=True)
    pat="|".join(re.escape(x) for x in names)
    m=re.search(r"\b(\d{1,2})\s+("+pat+r")\b",text)
    if m:
        day,month=int(m.group(1)),MONTHS[m.group(2)]
    else:
        m=re.search(r"\b("+pat+r")\s+(\d{1,2})\b",text)
        if m:
            month,day=MONTHS[m.group(1)],int(m.group(2))
        else:
            m=re.search(r"\b("+pat+r")\b",text)
            if m: month=MONTHS[m.group(1)]
    tr={1:"Ocak",2:"Şubat",3:"Mart",4:"Nisan",5:"Mayıs",6:"Haziran",7:"Temmuz",8:"Ağustos",9:"Eylül",10:"Ekim",11:"Kasım",12:"Aralık"}
    if year and month and day: label=f"{day} {tr[month]} {year}"
    elif year and month: label=f"{tr[month]} {year}"
    elif year: label=str(year)
    else: label=""
    return year,month,day,label

def import_chronology():
    folder=VAULT/"Tarihi Olaylar"/"Olaylar"
    if not folder.is_dir(): return None
    years,undated={},[]
    for path in sorted(folder.glob("*.md"),key=lambda p:p.name.casefold()):
        rel=path.relative_to(VAULT).as_posix()
        doc=read_doc(rel)
        if not doc: continue
        year,month,day,label=parse_event_date(path.stem,doc["title"])
        if "Akşam yemeği" in doc["title"] and year is None:
            year,month,day,label=1940,11,0,"Kasım 1940 · gün belirtilmemiş"
        rec=node("chronology",doc,label)
        if year is None: undated.append(rec)
        else: years.setdefault(year,[]).append((month,day,doc["title"],rec))
    roots=[]
    for year in sorted(years):
        events=[x[3] for x in sorted(years[year],key=lambda x:(x[0],x[1],x[2].casefold()))]
        roots.append(group("chronology",str(year),"YIL",f"{year} yılına ait {len(events)} tarihsel kayıt.",events,"year-"+str(year)))
    if undated:
        roots.append(group("chronology","Tarihi belirtilmeyen kayıtlar","TARİHİ BELİRTİLMEMİŞ","Kaynak notlarda kesin tarih verilmeyen olaylar.",undated,"undated-events"))
    return {"id":"chronology","title":"Kronoloji","description":"1938'den başlayarak alternatif tarih çizgisindeki olaylar. Yıl düğümlerini aç, olayları seç ve kayıtlar arasındaki bağlantıları izle.","view":"tree","label":"DALLANAN OLAY AĞACI","order":1,"nodes":roots}

def import_world():
    base="Alternatif Tarih/"
    overview=[]
    for rel in ["Ana Evren.md","Dünya/Genel Dünya.md","Dünya/Türkiye.md","Dünya/Almanya.md","Dünya/Amerika.md","Dünya/Diğer Devletler.md","Dünya/Dünya Paylaşımı 1946.md"]:
        full=base+rel
        doc=read_doc(full)
        if doc: overview.append(node("world",doc))
    sections=[]
    if overview:
        sections.append(group("world","Ana dünya ve devletler","DÜNYA DOSYALARI","Alternatif dünyanın tarihçesi, büyük güçleri ve 1946 paylaşım düzeni.",overview,"world-overview"))
    pdir=VAULT/base/"Dünya"/"Ülke Perspektifleri"
    perspectives=[]
    if pdir.is_dir():
        for path in sorted(pdir.glob("*.md"),key=lambda p:p.name.casefold()):
            rel=path.relative_to(VAULT).as_posix()
            doc=read_doc(rel)
            if doc: perspectives.append(node("world",doc))
    if perspectives:
        sections.append(group("world","Ülke perspektifleri","1938–1946","Aynı tarihsel dönemi farklı ülkelerin bakış açısından inceleyen notlar.",perspectives,"country-perspectives"))
    decades=[]
    for rel in ["Tarih/1940 - 1950.md","Tarih/1950.md","Tarih/1960.md","Tarih/1970.md","Tarih/1980.md"]:
        doc=read_doc(base+rel)
        if doc: decades.append(node("world",doc))
    if decades:
        sections.append(group("world","Dönem kayıtları","1940–1980","Savaş sonrası on yılların siyasi ve toplumsal gelişmeleri.",decades,"decade-records"))
    canon=[]
    for rel in ["Aslı Olan Düzen/World/Politics/Büyük Türk İmparatorluğu.md","Aslı Olan Düzen/World/Politics/Kanat.md"]:
        doc=read_doc(rel)
        if doc: canon.append(node("world",doc))
    if canon:
        sections.append(group("world","Devlet ve toplumsal sistem","KANON KAYITLARI","Yerleşik kanon olarak kaydedilmiş devlet ve toplumsal sistem notları.",canon,"state-and-social-system"))
    if not sections: return None
    return {"id":"world","title":"Dünya ve tarih","description":"Alternatif tarihin devletleri, dünya paylaşımı, ülke perspektifleri ve savaş sonrası on yıllar.","view":"catalogue","label":"DÜNYA KAYITLARI","order":2,"nodes":sections}

def import_characters():
    root=VAULT/"Alternatif Tarih"/"Karakterler"
    if not root.is_dir(): return None
    groups=[]
    folders=[("Ana ve Destek Karakterler","Ana ve destek karakterler","Romanın merkezindeki kişiler, aile üyeleri ve destek karakterleri."),("siyasi karakterler","Siyasi tarih ve soy","Türkiye'nin alternatif siyasi tarihindeki liderler ve aile geçmişi.")]
    for folder_name,title,summary in folders:
        folder=root/folder_name
        records=[]
        if folder.is_dir():
            for path in sorted(folder.glob("*.md"),key=lambda p:p.name.casefold()):
                rel=path.relative_to(VAULT).as_posix()
                doc=read_doc(rel)
                if not doc: continue
                lines=[]
                for line in doc["content"].splitlines():
                    if re.match(r"^\s*\*\*(Boyu?|Boy|Saç|Göz|Fiziksel yapı|En sevdiği renk|En Sevdiği Renk|Giyim tarzı|Giyim Tarzı)\s*:",line,re.I):
                        continue
                    lines.append(line)
                doc["content"]="\n".join(lines).strip()
                records.append(node("characters",doc))
        if records:
            groups.append(group("characters",title,"KARAKTER DOSYALARI",summary,records,slug(folder_name)))
    if not groups: return None
    return {"id":"characters","title":"Karakterler","description":"Romanın karakterleri ve alternatif tarihteki siyasi figürler.","view":"catalogue","label":"KİŞİ DOSYALARI","order":3,"nodes":groups}

def import_institutions():
    rel="Kuruluşlar/Hilalifiyet Merkezi - İstanbul.md"
    doc=read_doc(rel)
    if not doc: return None
    return {"id":"institutions","title":"Kurumlar","description":"Yayımlanmasına uygun kurumsal kayıtlar ve kurum profilleri.","view":"catalogue","label":"KURUM DOSYALARI","order":4,"nodes":[node("institutions",doc)]}

def import_technology():
    rel="Alternatif Tarih/Karakterler/Ana ve Destek Karakterler/Necdet Atalay.md"
    doc=read_doc(rel)
    if not doc: return None
    entry={"id":"technology-ta-85-gokkanat","path":rel,"sourceName":"TA-85 Gökkanat","title":"TA-85 Gökkanat","date":"Prototip dönemi: 1943","summary":"Türk uçan kanat tipi bombardıman uçağı projesi.","content":"**TA-85 Gökkanat**, evrende yer alan Türk uçan kanat tipi bombardıman uçağı projesidir. Necdet Atalay'ın karakter dosyası, uçağın yapımında görev aldığını kaydeder. Bu katalog yalnızca genel ve yayımlanabilir tanıtım bilgisini içerir; taslak veya gizli teknik dosyalar aktarılmamıştır.","order":1,"aliases":["Gökkanat","TA-85"],"children":[],"links":[]}
    return {"id":"technology","title":"Teknoloji","description":"Evrenin araç ve teknoloji projelerine ait yayımlanabilir genel kayıtlar.","view":"catalogue","label":"TEKNOLOJİ KATALOĞU","order":5,"nodes":[entry]}

def attach_links(categories):
    index={}
    def walk(nodes,cat_id,ancestors):
        for n in nodes:
            n["categoryId"]=cat_id
            n["ancestors"]=list(ancestors)
            for alias in [n.get("title",""),n.get("sourceName","")]+n.get("aliases",[]):
                if alias: index.setdefault(normalize(alias),(cat_id,n))
            walk(n.get("children",[]),cat_id,ancestors+[n["id"]])
    for cat in categories: walk(cat.get("nodes",[]),cat["id"],[])
    def resolve(nodes):
        for n in nodes:
            links=[]
            seen=set()
            for match in WIKILINK.finditer(n.get("content","")):
                found=index.get(normalize(match.group(1)))
                if found:
                    cat_id,target=found
                    key=(cat_id,target["id"])
                    if key!=(n["categoryId"],n["id"]) and key not in seen:
                        seen.add(key)
                        links.append({"categoryId":cat_id,"id":target["id"],"title":target["title"],"date":target.get("date","")})
            n["links"]=links
            resolve(n.get("children",[]))
    for cat in categories: resolve(cat.get("nodes",[]))

def manual_categories():
    root=ROOT/"content"/"archives"
    categories=[]
    reserved={"chronology","world","characters","institutions","technology"}
    if not root.is_dir(): return categories
    import json
    for folder in sorted(root.iterdir(),key=lambda p:p.name.casefold()):
        if not folder.is_dir() or folder.name in reserved or folder.name.startswith("_"): continue
        config_file=folder/"_archive.json"
        cfg=json.loads(config_file.read_text(encoding="utf-8")) if config_file.is_file() else {"title":folder.name.title(),"view":"tree","order":99}
        records=[]
        for path in sorted(folder.rglob("*.md"),key=lambda p:p.as_posix().casefold()):
            rel=path.relative_to(folder).as_posix()
            raw=path.read_text(encoding="utf-8")
            doc={"title":path.stem,"summary":"","content":raw,"aliases":[],"sourceName":path.stem,"path":rel}
            records.append(node(folder.name,doc))
        categories.append({"id":folder.name,"title":cfg.get("title",folder.name.title()),"description":cfg.get("description",""),"view":cfg.get("view","tree"),"label":cfg.get("label","ARŞİV"),"order":cfg.get("order",99),"nodes":records})
    return categories

def flatten(nodes):
    out=[]
    for n in nodes:
        out.append(n)
        out.extend(flatten(n.get("children",[])))
    return out

def discover_archives():
    cats=[]
    for fn in [import_chronology,import_world,import_characters,import_institutions,import_technology]:
        cat=fn()
        if cat: cats.append(cat)
    cats += manual_categories()
    cats.sort(key=lambda c:(c.get("order",99),c["title"].casefold()))
    attach_links(cats)
    return {"categories":cats}

def build():
    root=Path(__file__).resolve().parents[1]
    dist=root/"dist"
    if dist.exists(): shutil.rmtree(dist)
    dist.mkdir(parents=True)
    for name in ["index.html","robots.txt","sitemap.xml"]:
        src=root/name
        if src.is_file(): shutil.copy2(src,dist/name)
    assets=root/"assets"
    if assets.is_dir(): shutil.copytree(assets,dist/"assets")
    data=discover_archives()
    text=json.dumps(data,ensure_ascii=False,indent=2)+"\n"
    (root/"archives.json").write_text(text,encoding="utf-8")
    (dist/"archives.json").write_text(text,encoding="utf-8")
    print("Site build completed.")
    total=0
    for cat in data["categories"]:
        count=len(flatten(cat.get("nodes",[])))
        total+=count
        print(f" - {cat['title']}: {count} records")
    print(f"Total: {total} public records.")

if __name__=="__main__":
    import shutil
    import json
    build()
