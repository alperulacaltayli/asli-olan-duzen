#!/usr/bin/env python3
"""Read selected, approved public notes from the Obsidian vault."""
from __future__ import annotations
import json
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

def normalize_country(value):
    key = normalize(value)
    aliases = {
        "turkish": "turkish", "turk": "turkish", "turkiye": "turkish", "turkey": "turkish",
        "turkiye arsivi": "turkish", "turk arsivi": "turkish",
        "german": "german", "germany": "german", "alman": "german", "almanya": "german",
        "deutsch": "german", "deutschland": "german", "german reich": "german", "alman arsivi": "german",
        "both": "both", "shared": "both", "common": "both", "ortak": "both",
        "her iki arsiv": "both",
    }
    return aliases.get(key)


def apply_default_leaf_country(nodes, country, inherited_country=None):
    """Tag actual records, inheriting an explicit country from a parent folder."""
    for item in nodes or []:
        item_country = item.get("country") or inherited_country
        children = item.get("children", [])
        if children:
            apply_default_leaf_country(children, country, item_country)
        elif not item.get("country"):
            item["country"] = item_country or country


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
    status = meta.get("status", "").casefold().strip()
    tags = meta.get("tags", "").casefold()
    privacy = meta.get("gizlilik", meta.get("privacy", "")).casefold()
    visibility_key = next((key for key in ("visibility", "publication", "yayın") if key in meta), None)
    visibility = meta.get(visibility_key, "").casefold().strip() if visibility_key else ""
    public_values = {"public", "kamuya açık", "kamuya acik", "herkese açık", "herkese acik"}
    if visibility_key and visibility not in public_values:
        return None
    blocked = ("draft", "proposed", "taslak", "yazar onayı bekliyor", "approval pending",
               "gizli", "classified", "internal", "private", "confidential", "unlisted", "spoiler")
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
    return {"title":title,"summary":summary,"content":content,"aliases":aliases,"sourceName":path.stem,"path":relative.replace("\\","/"),"country":normalize_country(meta.get("country", meta.get("ülke", "")))}

def node(category, doc, date=""):
    record = {"id":category+"-"+slug(doc["path"]),"path":doc["path"],"sourceName":doc["sourceName"],"title":doc["title"],"date":date,"summary":doc["summary"],"content":doc["content"],"order":999,"aliases":doc["aliases"],"children":[],"links":[]}
    country = normalize_country(doc.get("country", ""))
    if country:
        record["country"] = country
    for field in ("character", "character_group", "record_type", "theme"):
        value = str(doc.get(field, "")).strip()
        if value:
            record[field] = value
    return record

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
    seen_titles=set()
    for path in sorted(folder.glob("*.md"),key=lambda p:p.name.casefold()):
        rel=path.relative_to(VAULT).as_posix()
        doc=read_doc(rel)
        if not doc: continue
        year,month,day,label=parse_event_date(path.stem,doc["title"])
        if "Akşam yemeği" in doc["title"] and year is None:
            year,month,day,label=1940,11,0,"Kasım 1940 · gün belirtilmemiş"
        rec=node("chronology",doc,label)
        seen_titles.add(normalize(doc["title"]))
        if year is None: undated.append(rec)
        else: years.setdefault(year,[]).append((month,day,doc["title"],rec))

    manual_root = ROOT / "content" / "archives" / "chronology"
    if manual_root.is_dir():
        for path in sorted(manual_root.rglob("*"), key=lambda item: item.as_posix().casefold()):
            if not path.is_file() or path.name.lower() in {"readme.md", "index.md", "index.txt"}:
                continue
            doc = read_public_archive_note(path, manual_root)
            if not doc or normalize(doc["title"]) in seen_titles:
                continue
            year,month,day,label = parse_event_date(path.stem + " " + doc.get("date", ""), doc["title"])
            rec = node("chronology", doc, label or doc.get("date", ""))
            rec["order"] = doc.get("order", 999)
            if year is None:
                undated.append(rec)
            else:
                years.setdefault(year, []).append((month,day,doc["title"],rec))
            seen_titles.add(normalize(doc["title"]))
    roots=[]
    for year in sorted(years):
        events=[x[3] for x in sorted(years[year],key=lambda x:(x[0],x[1],x[2].casefold()))]
        roots.append(group("chronology",str(year),"YIL",f"{year} yılına ait {len(events)} tarihsel kayıt.",events,"year-"+str(year)))
    if undated:
        roots.append(group("chronology","Tarihi belirtilmeyen kayıtlar","TARİHİ BELİRTİLMEMİŞ","Kaynak notlarda kesin tarih verilmeyen olaylar.",undated,"undated-events"))
    return {"id":"chronology","title":"Kronoloji","description":"1938'den başlayarak alternatif tarih çizgisindeki olaylar. Yıl düğümlerini aç, olayları seç ve kayıtlar arasındaki bağlantıları izle.","view":"tree","label":"DALLANAN OLAY AĞACI","order":1,"nodes":roots}

def make_public_character(category, spec):
    """Create a short, spoiler-safe character card from an approved source note."""
    if spec.get("profile_only"):
        doc = {"sourceName": spec["name"], "title": spec["name"], "country": spec.get("country", "turkish")}
    else:
        doc = read_doc(spec["path"])
    if not doc:
        return None

    fields = []
    if spec.get("birth"):
        fields.append(f"**Doğum:** {spec['birth']}")
    if spec.get("age"):
        fields.append(f"**Yaş (1985):** {spec['age']}")
    if spec.get("role"):
        fields.append(f"**Genel rol:** {spec['role']}")
    if spec.get("appearance"):
        fields.append(f"**Dış görünüş:** {spec['appearance']}")
    if spec.get("personality"):
        fields.append(f"**Kişilik:** {spec['personality']}")

    content = "\n\n".join(fields)
    summary = spec.get("summary") or spec.get("personality", "")
    return {
        "id": category + "-" + slug(spec["key"]),
        "path": spec["path"],
        "sourceName": doc["sourceName"],
        "title": spec["name"],
        "date": spec.get("date", ""),
        "summary": summary,
        "content": content,
        "order": spec.get("order", 999),
        "aliases": spec.get("aliases", [doc["title"], doc["sourceName"]]),
        "children": [],
        "links": [],
        "country": normalize_country(doc.get("country", "")) or normalize_country(spec.get("country", "turkish")) or "turkish",
    }

def make_character_group(title, date, summary, children, key):
    return group("characters", title, date, summary, children, key)

def import_characters():
    """Publish concise, consistent, non-spoiler character introductions only."""
    main_base = "Alternatif Tarih/Karakterler/Ana ve Destek Karakterler/"
    political_base = "Alternatif Tarih/Karakterler/siyasi karakterler/"

    main_specs = [
        {
            "key":"alev-acar", "path":main_base+"Alev Acar.md", "name":"Alev Acar",
            "date":"1968 · 17 yaş", "birth":"1968", "age":"17",
            "role":"Öğrenci · 2. Kanat · sivil pilotluk hedefi",
            "appearance":"Düz kızıl saçlı ve ela gözlü.",
            "personality":"Neşeli, konuşkan, uyumlu ve arkadaşlarına bağlı.",
            "aliases":["Alev Acar"]
        },
        {
            "key":"asena-korkut", "path":main_base+"Asena Korkut.md", "name":"Asena Korkut",
            "date":"1968 · 17 yaş", "birth":"1968", "age":"17",
            "role":"Öğrenci · 5. Kanat",
            "appearance":"Siyah, hafif kızıl tonlu saçları, kahverengi gözleri ve gözlüğü vardır.",
            "personality":"Konuşkan, sosyal, anlayışlı ve insan ilişkilerinde becerikli.",
            "aliases":["Asena Korkut"]
        },
        {
            "key":"aylin-aksoy", "path":main_base+"Aylin Aksoy.md", "name":"Aylin Aksoy",
            "date":"1968 · 17 yaş", "birth":"1968", "age":"17",
            "role":"Öğrenci · 3. Kanat · hukuk alanına ilgi duyuyor",
            "appearance":"Uzun, kıvırcık kumral saçlı ve koyu gözlü.",
            "personality":"Sakin, dikkatli, gözlemci ve planlı.",
            "aliases":["Aylin Aksoy"]
        },
        {
            "key":"tomris-ilter", "path":main_base+"Tomris İlter.md", "name":"Tomris İlter",
            "date":"1968 · 17 yaş", "birth":"1968", "age":"17",
            "role":"Öğrenci · 6. Kanat",
            "appearance":"Uzun siyah saçlı ve koyu gözlü.",
            "personality":"Kendine güvenen, ciddi, kararlı ve yönetici yönü güçlü.",
            "aliases":["Tomris İlter","TOMRİS İLTER"]
        },
        {
            "key":"ismail-yagiz-aslan", "path":main_base+"İsmail Yağız Aslan.md", "name":"İsmail Yağız Aslan",
            "date":"1968 · 17 yaş", "birth":"1968", "age":"17",
            "role":"Öğrenci",
            "appearance":"Siyah saçlı, kahverengi gözlü; rahat ve gündelik giyimi tercih eder.",
            "personality":"Neşeli, esprili ve samimi; gerektiğinde kararlı ve odaklı.",
            "aliases":["İsmail Yağız Aslan","İso"]
        },
        {
            "key":"muhammed-mete", "path":main_base+"Muhammed Mete.md", "name":"Muhammed Mete",
            "date":"1968 · 17 yaş", "birth":"1968", "age":"17",
            "role":"Öğrenci · 4. Kanat · sivil havacılığa ilgi duyuyor",
            "appearance":"Siyah, hafif kıvırcık saçlı ve kahverengi gözlü.",
            "personality":"Sakin, ölçülü, uyumlu ve yakın çevresinde konuşkan.",
            "aliases":["Muhammed Mete"]
        },
        {
            "key":"oguz-kagan-atalay", "path":main_base+"Oğuz Kağan Atalay.md", "name":"Oğuz Kağan Atalay",
            "date":"1968 · 17 yaş", "birth":"3 Ocak 1968 · İstanbul, Üsküdar", "age":"17",
            "role":"Öğrenci · 3. Kanat · havacılığa ilgi duyuyor",
            "appearance":"Belirgin yüz hatlarına, kızıl saçlara ve düzenli bir görünüme sahiptir.",
            "personality":"Sakin, soğukkanlı, disiplinli, gözlemci ve teknik konulara meraklı.",
            "aliases":["Oğuz Kağan Atalay"]
        },
        {
            "key":"aysel-atalay", "path":main_base+"Aysel Atalay.md", "name":"Aysel Atalay",
            "date":"1947 · 38 yaş", "birth":"1947", "age":"38",
            "role":"Atalay ailesinin annesi",
            "appearance":"Sade ve zarif bir giyim tarzını tercih eder.",
            "personality":"Sakin, sabırlı, anlayışlı ve koruyucu.",
            "aliases":["Aysel Atalay"]
        },
        {
            "key":"cengiz-atalay", "path":main_base+"Cengiz Atalay.md", "name":"Cengiz Atalay",
            "date":"1942 · 43 yaş", "birth":"1942", "age":"43",
            "role":"Askerî uçak mühendisi",
            "appearance":"Düzenli ve klasik giyinir; resmî ve hafif askerî çizgileri tercih eder.",
            "personality":"Özgüvenli, enerjik, meraklı ve çalışkan.",
            "aliases":["Cengiz Atalay"]
        },
        {
            "key":"meliha-atalay", "path":main_base+"Meliha Atalay.md", "name":"Meliha Atalay",
            "date":"1976 · 9 yaş", "birth":"1976", "age":"9",
            "role":"Öğrenci",
            "appearance":"Yaşına uygun, sade ve rahat kıyafetler tercih eder.",
            "personality":"Çalışkan, kararlı, inatçı ve azimli.",
            "aliases":["Meliha Atalay"]
        },
        {
            "key":"muhammed-atalay", "path":main_base+"Muhammed Atalay.md", "name":"Muhammed Atalay",
            "date":"1974 · 11 yaş", "birth":"1974", "age":"11",
            "role":"Öğrenci · mühendisliğe ilgi duyuyor",
            "appearance":"Yaşına uygun, sade ve rahat giyinir.",
            "personality":"Meraklı, hareketli ve teknik konulara ilgili.",
            "aliases":["Muhammed Atalay"]
        },
        {
            "key":"nec-det-atalay", "path":main_base+"Necdet Atalay.md", "name":"Necdet Atalay",
            "date":"1918 · 67 yaş", "birth":"1918", "age":"67",
            "role":"Emekli askerî uçak mühendisi",
            "appearance":"Sade, klasik ve düzenli giyinir.",
            "personality":"Ağırbaşlı, disiplinli, otoriter ve az konuşan.",
            "aliases":["Necdet Atalay"]
        },
        {
            "key":"sabiha-atalay", "path":main_base+"Sabiha Atalay.md", "name":"Sabiha Atalay",
            "date":"1923 · 62 yaş", "birth":"1923", "age":"62",
            "role":"Atalay ailesinin büyüğü",
            "appearance":"Sade ve klasik kıyafetler tercih eder.",
            "personality":"Sakin, sabırlı, anlayışlı ve aile odaklı.",
            "aliases":["Sabiha Atalay"]
        },
        {
            "key":"naciye-kaya", "path":main_base+"Naciye Kaya.md", "name":"Naciye Kaya",
            "date":"1920 · 65 yaş", "birth":"1920", "age":"65",
            "role":"Kaya ailesinin büyüğü",
            "appearance":"Sade ve geleneksel bir giyim tarzına sahiptir.",
            "personality":"Girişken, konuşkan, açık sözlü ve pratik zekâlı.",
            "aliases":["Naciye Kaya"]
        },
        {
            "key":"riza-kaya", "path":main_base+"Rıza Kaya.md", "name":"Rıza Kaya",
            "date":"1916 · 69 yaş", "birth":"1916", "age":"69",
            "role":"Kaya ailesinin büyüğü",
            "appearance":"Sade ve düzenli giyinir.",
            "personality":"Sakin, ağırbaşlı, geleneklerine bağlı ve sorumluluk sahibi.",
            "aliases":["Rıza Kaya"]
        },
    ]

    political_specs = [
        {
            "key":"abdullah-keser", "path":political_base+"Abdullah.md", "name":"Abdullah Keser",
            "date":"Yaklaşık 1770–1830'lar", "birth":"Yaklaşık 1770 · Giresun, Kuşköy",
            "role":"Keser soyunun eski kuşağı · demirci",
            "personality":"Sert mizaçlı, az konuşan, çalışkan ve ailesine bağlı.",
            "aliases":["Abdullah","Abdullah Keser"]
        },
        {
            "key":"oguz-keser", "path":political_base+"Oğuz.md", "name":"Oğuz Keser",
            "date":"1802–1898", "birth":"1802 · Giresun, Kuşköy",
            "role":"Keser soyunun ikinci kuşağı · demirci",
            "personality":"Geleneklerine bağlı, dürüst, sevecen ve güçlü iradeli.",
            "aliases":["Oğuz","Oğuz Keser"]
        },
        {
            "key":"gul-keser", "path":political_base+"Gül.md", "name":"Gül Keser",
            "date":"Yaklaşık 1810 doğumlu", "birth":"Yaklaşık 1810 · Giresun çevresi",
            "role":"Keser ailesinin ikinci kuşağı",
            "personality":"Sabırlı, sezgileri güçlü, birleştirici ve aile odaklı.",
            "aliases":["Gül","Gül Keser"]
        },
        {
            "key":"kaan-keser", "path":political_base+"Kaan.md", "name":"Kaan Keser",
            "date":"1846–1904", "birth":"1846 · Giresun, Kuşköy",
            "role":"Keser soyunun üçüncü kuşağı · demirci",
            "personality":"Sakin, azimli, tutkulu ve sorumluluk sahibi.",
            "aliases":["Kaan","Kaan Keser"]
        },
        {
            "key":"ali-keser", "path":political_base+"Ali.md", "name":"Ali Keser",
            "date":"Keser soyunun üçüncü kuşağı", "role":"Tarım işleriyle uğraşır; dönem dönem demircilik yapar.",
            "personality":"Hareketli, meraklı, bağımsız ve zaman zaman çabuk öfkelenen.",
            "aliases":["Ali","Ali Keser"]
        },
        {
            "key":"firuze-keser", "path":political_base+"Furize.md", "name":"Firuze Keser",
            "date":"Keser soyunun üçüncü kuşağı", "role":"Keser ailesinin bir üyesi",
            "personality":"Sabırlı, şefkatli, içine kapanık ve gerektiğinde dirençli.",
            "aliases":["Firuze","Firuze Keser","Furize"]
        },
        {
            "key":"alperen-keser", "path":political_base+"Alperen.md", "name":"Alperen Keser",
            "date":"1899 doğumlu · 1938'de yönetimi devraldı", "birth":"1899 · Giresun, Kuşköy",
            "role":"Asker ve devlet adamı · 1938'de yönetimi devralan lider",
            "personality":"Disiplinli, kararlı, milliyetçi ve sanayileşme yanlısı.",
            "aliases":["Alperen","Alperen Keser"]
        },
        {
            "key":"ismail-karaslan", "path":political_base+"İsmail Karaslan.md", "name":"İsmail Karaslan",
            "date":"1915 doğumlu · Alperen Keser sonrasındaki lider", 
            "birth":"1915 · Hatay",
            "role":"Asker ve devlet adamı",
            "personality":"Disiplinli, devletçi, temkinli ve güçlü merkezi yönetim yanlısı.",
            "aliases":["İsmail Karaslan"]
        },
        {
            "key":"selim-arkan", "path":political_base+"Selim Arkan.md", "name":"Selim Arkan",
            "date":"1939 doğumlu · 1985'te Ulu Han",
            "birth":"1939 · Ankara",
            "role":"Siyasetçi ve devlet adamı",
            "personality":"Soğukkanlı, pragmatik, devletçi ve stratejik düşünen.",
            "aliases":["Selim Arkan"]
        },
    ]

    extra_student_specs = [
        {
            "key":"alper-ulac-altayli", "name":"Alper Ulaç Altaylı",
            "date":"1968 · 17 yaş", "birth":"1968", "age":"17",
            "role":"Öğrenci · 6. Kanat · Üsküdar Milli İlim ve İrfan Mektebi okul başkanı",
            "appearance":"Düzenli, ölçülü ve sade giyinir; bulunduğu ortamda dikkat çekmekten çok kontrolü elinde tutmayı tercih eder.",
            "personality":"Sakin, hesapçı, stratejik ve kontrol ihtiyacı yüksek.",
            "summary":"Üsküdar Mektebi'nin altı kanatlı başkanı; otoritesini kürsüden çok bilgi, gözlem ve ilişkileri yöneterek kurar.",
            "profile_only":True, "country":"turkish", "aliases":["Alper","Alper Ulaç Altaylı"]
        }
    ]
    state_specs = [
        {
            "key":"kaan-demirsoy", "name":"Kaan Demirsoy", "date":"1936 doğumlu",
            "birth":"1936", "role":"Başbuyruk · Ulu Han'ın iradesini bağlayıcı emre dönüştüren makam",
            "personality":"Sessiz, titiz, sabırlı ve kayıt düzenine bağlı.",
            "summary":"İmparatorluk yönetiminin emir, kararname ve kayıt düzenini ayakta tutan Başbuyruk.",
            "profile_only":True, "country":"turkish"
        },
        {
            "key":"sabiha-erten", "name":"Sabiha Erten", "date":"1945 doğumlu · 40 yaş",
            "birth":"1945", "age":"40", "role":"Başbuyruk Kalemi Müsteşarı",
            "personality":"Sessiz, dikkatli, titiz ve gerektiğinde itiraz etmekten çekinmeyen.",
            "summary":"Kararname nüshalarının, mühür sırasının ve gizli tutanakların düzenini takip eden bürokrat.",
            "profile_only":True, "country":"turkish"
        },
        {
            "key":"mete-kutlu", "name":"Mete Kutlu", "date":"1931 doğumlu · 54 yaş",
            "birth":"1931", "age":"54", "role":"İmparatorluk İstihbarat Başkanı",
            "personality":"Sakin, ölçülü, sabırlı ve dikkatli bir dinleyici.",
            "summary":"Dış istihbarat ve Reich masasını yöneten; bildiğini hemen açığa vurmayan istihbarat başkanı.",
            "profile_only":True, "country":"turkish"
        },
        {
            "key":"rana-tozun", "name":"Rana Tözün", "date":"1938 doğumlu · 47 yaş",
            "birth":"1938", "age":"47", "role":"Bilim ve Gök Araştırmaları Başkanı",
            "personality":"Sakin, kesin, sabırlı ve veriye bağlı.",
            "summary":"Gök Kutup, sensör çalışmaları ve imparatorluğun bilim programlarından sorumlu üst düzey yönetici.",
            "profile_only":True, "country":"turkish"
        },
        {
            "key":"ziya-arat", "name":"Ziya Arat", "date":"1934 doğumlu · 51 yaş",
            "birth":"1934", "age":"51", "role":"Maarif ve Gençlik Nazırı",
            "personality":"Enerjik, ikna edici ve siyasî açıdan dikkatli.",
            "summary":"Mekteplerin, müfredatın ve imparatorluk genelindeki Kanat sisteminin sorumlusu.",
            "profile_only":True, "country":"turkish"
        },
        {
            "key":"haluk-sancar", "name":"Haluk Sancar", "date":"1927 doğumlu · 58 yaş",
            "birth":"1927", "age":"58", "role":"Afrika Umumi Valisi",
            "personality":"Enerjik, konuşkan, ikna edici ve siyasî denge gözeten.",
            "summary":"Afrika'daki reform hedefleri ile taşradaki keyfî uygulamalar arasındaki çelişkinin merkezindeki vali.",
            "profile_only":True, "country":"turkish"
        }
    ]
    reich_specs = [
        {
            "key":"reinhard-falkenhorst", "name":"Reinhard Falkenhorst", "date":"1922 doğumlu · 63 yaş",
            "birth":"1922", "age":"63", "role":"Führer und Reichskanzler des Großdeutschen Reiches",
            "personality":"Ağır, soğuk, sabırlı ve hesapçı.",
            "summary":"Reich'ın tepesindeki Führer; parti, SS, ordu ve sanayi arasındaki dengeyi kendi otoritesi altında tutar.",
            "profile_only":True, "country":"german"
        },
        {
            "key":"martin-kessler", "name":"Martin Kessler", "date":"1930 doğumlu · 55 yaş",
            "birth":"1930", "age":"55", "role":"Führer Yardımcısı · Parti Kanzelleyi Başkanı",
            "personality":"Nazik görünen, sabırlı ve siyasî bağlantıları güçlü.",
            "summary":"Reich içindeki atamaları ve parti disiplinini yöneten etkili iktidar aracısı.",
            "profile_only":True, "country":"german"
        },
        {
            "key":"ulrich-von-havel", "name":"Ulrich von Havel", "date":"1932 doğumlu · 53 yaş",
            "birth":"1932", "age":"53", "role":"Reich Dışişleri Bakanı",
            "personality":"Kibar, sabırlı, hesapçı ve diplomatik baskı kurabilen.",
            "summary":"Türkiye ile ilişkilerde Reich'ın çıkarlarını nezaket ve koşullu teklifler üzerinden gözeten bakan.",
            "profile_only":True, "country":"german"
        },
        {
            "key":"friedrich-wulfhart", "name":"Friedrich Wulfhart", "date":"1925 doğumlu · 60 yaş",
            "birth":"1925", "age":"60", "role":"Reichsführer-SS und Chef der Reichssicherheit",
            "personality":"Sessiz, düzen takıntılı, ideolojik açıdan katı ve hesaplı.",
            "summary":"Nazi rejiminin güvenlik ve baskı aygıtını yöneten SS lideri.",
            "profile_only":True, "country":"german"
        },
        {
            "key":"konrad-weissmann", "name":"Konrad Weissmann", "date":"1933 doğumlu · 52 yaş",
            "birth":"1933", "age":"52", "role":"Baş Nükleer Fizikçi · SFA-P Polaris",
            "personality":"Sabırsız, keskin, kibirli ve veriye odaklı.",
            "summary":"Reich'ın yüksek enerji fiziği ve özel teknoloji programlarında öne çıkan bilim insanı.",
            "profile_only":True, "country":"german"
        }
    ]

    main_nodes = {}
    for spec in main_specs:
        rec = make_public_character("characters", spec)
        if rec:
            main_nodes[spec["key"]] = rec

    political_nodes = {}
    for spec in political_specs:
        rec = make_public_character("characters", spec)
        if rec:
            political_nodes[spec["key"]] = rec

    for spec in extra_student_specs:
        rec = make_public_character("characters", spec)
        if rec:
            main_nodes[spec["key"]] = rec

    state_nodes = {}
    for spec in state_specs:
        rec = make_public_character("characters", spec)
        if rec:
            state_nodes[spec["key"]] = rec

    reich_nodes = {}
    for spec in reich_specs:
        rec = make_public_character("characters", spec)
        if rec:
            reich_nodes[spec["key"]] = rec

    expansions = {
        "oguz-kagan-atalay": (
            "Üçüncü kanatlı Oğuz, iki kuşaktır uçak mühendisi yetiştiren Atalay ailesinin havacılık mirasını kokpitte sürdürmek ister. Dedesi Necdet ve babası Cengiz uçakları tasarlayan ve geliştiren insanlardır; Oğuz'un kendi arzusu ise onları uçurmaktır. Teknik bilgisi ve teorik hazırlığı güçlüdür, ancak 1985'te henüz gerçek uçuş eğitimi almamıştır.\n\nSoğukkanlılığı, düzenli çalışması ve bağımsız hareket etme isteği onu güvenilir kılar. Buna karşılık başarısızlığı kişisel bir kusur gibi algılaması, duygularını bastırması ve aynı anda çok fazla konuya yönelmesi zayıf yanlarıdır. Başlangıçta güçlü devlet ve emir-komuta düşüncesine yakındır; yaşadıkları, disiplin ile vicdanı birbirinden ayırıp ayıramayacağını sorgulamasına yol açar.\n\nİsmail'le ortaokul yıllarından beri süren dostluğu, Aylin'le gelişen yakınlığı ve Alper'le benzer görünen fakat ahlaken ayrışan rekabeti, Oğuz'un kişisel dünyasını şekillendirir. Babası Cengiz'in hayatında açıklayamadığı boşluklar bulunması da aile geçmişini sorgulamasına neden olur."
        ),
        "alper-ulac-altayli": (
            "Alper, Üsküdar Milli İlim ve İrfan Mektebi'nin altı kanatlı okul başkanı ve Üsküdar Bloğu'nun lideridir. Yetkisini yalnızca resmî makamından almaz; okul içindeki insanları, ilişkileri ve bilgi akışını dikkatle izler. Panosu, notları ve dosyaları onun yönetim anlayışının uzantısıdır: kim hangi konuda yetenekli, kimin kiminle bağı var, hangi gelişme yaklaşan bir soruna dönüşebilir? Bu sorulara cevap arayarak çevresini düzenler.\n\nSakin konuşur ve nadiren sesini yükseltir. Otoritesini açık cezadan çok, karşısındakine ne bildiğini göstererek kurar. İnsanları çoğu zaman kabiliyetleri üzerinden değerlendirir; hedefi için yöntemlerini esnetebilmesi, onu etkili olduğu kadar ahlaken tartışmalı da kılar. Buna rağmen İsmail'e ve bir ölçüde Oğuz'a karşı gerçek bağlar taşır. Oğuz'la rekabetleri, benzer disiplin ve dış görünüşün ardında farklı ahlak anlayışlarının bulunmasından kaynaklanır. Tomris'le geçmişte Hilalifiyet çevresinde yaşanan yenilgi de iki okul yöneticisi arasındaki gerilimin önemli zeminidir."
        ),
        "ismail-yagiz-aslan": (
            "İsmail, beş kanatlı okul başkan yardımcısıdır ve gelecekte siyasete girmeyi ister. Arkadaş çevresinde mizahı, rahat tavrı ve samimiyetiyle tanınır. İlgisini çekmeyen işlerde üşengeç davranabilir; ancak bir meseleyi gerçekten önemsediğinde uzun süre odaklanır ve çevresindekilerin beklemediği kadar pratik çözümler üretebilir. Bu nedenle onu yalnızca sınıfın şakacısı olarak görmek yanıltıcıdır.\n\nOğuz'la ortaokulun altıncı sınıfında tanışmış, yıllar içinde güçlü bir arkadaşlık kurmuştur. Oğuz'un ona taktığı İso lakabı, aralarındaki rahat ve samimi dili yansıtır. Alper'in yardımcısı olarak okul yönetiminde yer alması, onu dostluk çevresi ile öğrenci siyaseti arasında tutar. İsmail'in mizahı çoğu zaman gerginliği dağıtır; fakat konu ciddileştiğinde aynı rahatlığın altında kararlı bir taraf bulunduğu görülür."
        ),
        "muhammed-mete": (
            "Muhammed Mete, dördüncü kanatlı bir öğrenci ve sivil pilot adayıdır. İlk karşılaşmada ağırbaşlı ve mesafeli görünse de güvendiği insanların yanında konuşkan, neşeli ve enerjik olabilir. Farklı ortamlara hızlı uyum sağlaması, arkadaş grubunda çatışmayı büyütmek yerine denge kurmasına yardımcı olur.\n\nPilotluk onun için yalnızca bir meslek değildir; yeni yerler görmek, aynı noktaya bağlı kalmamak ve kendi hayatının yönünü seçebilmek anlamına gelir. Sadakat, samimiyet ve güvene önem verir. Sevdiği insanları kaybetmekten ve onları hayal kırıklığına uğratmaktan çekindiği için önemli kararlarında kendisini gereğinden fazla sorgulayabilir. Oğuz, Alev ve diğer arkadaşlarıyla kurduğu bağ, sınıfın daha sakin ama güvenilir damarını oluşturur. Oğuz'un kardeşi Muhammed Atalay ile aynı kişi değildir."
        ),
        "aylin-aksoy": (
            "Üç kanatlı Aylin, hukuk alanında ilerlemek isteyen, çevresini önce gözlemleyip sonra karar veren bir öğrencidir. İnsanlara kolayca güvenmez; fakat tanıdığı birini peşinen yargılamaz. Küçük ayrıntıları fark etmesi ve olayları uzun süre zihninde tartması, onu iyi bir gözlemci yapar. Bunun bedeli bazen fazla düşünerek karar vermeyi geciktirmesidir.\n\nSadakat, dürüstlük ve güven onun için temel değerlerdir. Bir arkadaşının yanlışını sırf yakın oldukları için savunmaz; gerçeği söylemenin de dostluğun parçası olduğuna inanır. Alev'le çocukluktan gelen arkadaşlığı bu iki karakterin birbirini tamamlamasını sağlar: Aylin düşünür ve ölçer, Alev daha çabuk harekete geçer. Oğuz'u ilk gördüğünde Alper'e benzetir; zamanla ikisinin sakinliğinin ve karar verme biçimlerinin farklı olduğunu fark eder. Tomris ve Asena'yla ilişkisi ise kişisel yakınlık ile kendisine verilen görev arasında denge kurmasını gerektirir."
        ),
        "alev-acar": (
            "İki kanatlı Alev, sınıfın hareketli ve iletişimi güçlü öğrencilerindendir. Yeni bir ortama girdiğinde uzun süre sessiz kalmaz; planlar değiştiğinde kolayca uyum sağlar ve yeni bir yol bulur. Bu canlı tavrı gerektiğinde ciddileşmesine engel değildir. Sivil pilotluk hedefi, hareket ve keşif isteğiyle birleşir.\n\nAlev için sadakat çok önemlidir; birine gerçekten bağlandıktan sonra onu yarı yolda bırakmayı kendine yakıştırmaz. Bununla birlikte güveni ilk anda bütünüyle vermez, karşısındaki insanı zaman içinde tanır. Aylin'le çocukluk arkadaşıdır: Aylin daha çok düşünürken Alev harekete geçer. Oğuz'u başlangıçta iyi niyetli ve güvenilir bulur; Muhammed Mete'yle de aynı arkadaş çevresinde yer alır."
        ),
        "tomris-ilter": (
            "Tomris, İstanbul Şarkın İlim ve Teknoloji Mektebi'nin altı kanatlı okul başkanıdır. Yönetmek onun için yalnızca bir görev değil, dünyayı anlaşılır ve denetlenebilir tutmanın yoludur. İnsanların davranışlarını, hafızalarını ve aralarındaki güç ilişkilerini dikkatle izler; birkaç adım sonrasını düşünerek hareket eder. Doğrudan konuşur, kendine güvenir ve kararsız görünmekten hoşlanmaz.\n\nTomris'in temel korkusu yenilmekten çok kontrolü kaybetmektir. Bu yüzden gerektiğinde kuralı esnetebilir, gerçeği saklayabilir veya insanları kendi planına göre yönlendirebilir. Düzenin korunmasını önemserken, aynı düzeni korumak için kendi koyduğu ilkeleri çiğneyebilmesi karakterinin ana çelişkisidir. Gelecekte millî istihbarat ve askerî güvenlik alanında görev almak ister. Asena'yı çocukluğundan beri en güvendiği kişi olarak görür. Alper'le Hilalifiyet'te yaşanan eski yenilgiye dayanan rekabeti ise kişisel bir hesap hâline gelmiştir. Oğuz'la henüz tanışmamıştır."
        ),
        "asena-korkut": (
            "Asena, Şarkın Mektebi'nin beş kanatlı başkan yardımcısıdır ve istihbarat alanında, özellikle saha görevlerinde ilerlemek ister. Tomris kadar kontrol odaklı değildir; insanları anlamak, konuşmalarından ve davranışlarından güven ilişkisi kurmak onun güçlü yanıdır. Sosyal, hareketli ve kolay iletişim kuran biri görünür; buna karşılık kendi yeterliliğini sık sık sorgular ve başarısız olduğunda bunu kişisel değeriyle karıştırabilir.\n\nTomris'le çocukluktan beri süren yakınlığı, onun en büyük gücü ve zayıflığıdır. Tomris'in kararlarını düşünmeden kabul etmez; tartar, fakat çoğu zaman onun yanında kalır. Bu bağlılık kör itaat değildir: Tomris'in yanlış yaptığını fark ettiğinde onu durdurabilecek ender kişilerden biri Asena'dır. Aylin ve Alev'le, Tomris'e kıyasla daha rahat ve doğal bir iletişim kurar. Bu nedenle iki okul arasındaki görev ilişkilerinde insanî bağları ve kişisel sadakati sürekli karşı karşıya gelir."
        ),
        "cengiz-atalay": (
            "Cengiz, Gökkanat programında çalışan askerî uçak mühendisidir. Meraklı, enerjik ve üretkendir; mekanik sorunları çözmek, mevcut sistemleri geliştirmek ve bir tasarımın zayıf noktasını bulmak onu motive eder. İşine duyduğu ilgi zaman zaman aile hayatındaki sorumluluklarının önüne geçebilir. 1942 doğumlu olması, Oğuz'un 1968'de doğduğu sırada yirmi altı yaşında olduğunu gösterir.\n\nOğuz'la güçlü bir ilişkisi vardır. Ona çalışma disiplini, sorumluluk alma ve teknik konulara sabırla yaklaşma alışkanlığı kazandırmıştır. Oğlunun askerî pilot olmasını ister; böylece ailedeki mühendislik geleneğinin başka bir biçimde sürmesini bekler. Aysel'le birbirini tamamlayan bir aile düzeni kurmuştur. Cengiz'in mesleki hayatındaki bazı boşluklar ve içine kapanması, Oğuz'un babasını yalnızca bir mühendis olarak değil, geçmişi olan bir insan olarak anlamaya çalışmasına yol açar."
        ),
        "aysel-atalay": (
            "Aysel, Atalay ailesinin ev içindeki duygusal dengesini koruyan kişidir. Sakin, sabırlı ve gözlemcidir; Cengiz'in işine yoğunlaşmasını ve Oğuz'un giderek ağırlaşan hedeflerini anlayışla karşılamaya çalışır. Ancak anlayışlı olması kaygı duymadığı anlamına gelmez. Özellikle Oğuz'un kendisini fazla zorlamasından ve tehlikeli bir mesleğe yönelmesinden endişelenir.\n\nAile içinde çoğu zaman doğrudan sorgulamak yerine küçük değişiklikleri fark eder ve doğru zamanı bekler. Cengiz'in başarılarıyla gurur duyar, Oğuz'a ise duygularını rahatça gösterebileceği güvenli bir alan sunar. Kendi isteklerini ailesinin gerisine atması, koruyucu yönünün aynı zamanda zayıflığıdır."
        ),
        "nec-det-atalay": (
            "Necdet, Atalay ailesinin havacılık geleneğinin ilk önemli halkası olan emekli askerî uçak mühendisidir. 1940'lı yıllardan itibaren askerî havacılık ve uzun menzilli uçak projelerinde çalışmıştır. Oğuz'a uçakları, kanat biçimlerini ve mühendisliğin gerektirdiği sabrı çocukluğundan itibaren anlatmıştır. Sevgisini uzun konuşmalarla değil, bilgi ve deneyim aktararak gösterir.\n\nSert, suskun ve disiplinlidir. Geçmişi anlatırken bazı ayrıntıları seçerek paylaşır; kimi meseleleri hiç açmaması, Oğuz'un tarih ve aile hafızasına yaklaşımını etkiler. 1965 Gökkanat hangarı olayı, Necdet'in geçmişindeki önemli bir dönüm noktasıdır. Bu olayın ayrıntıları karakter tanıtımında açıklanmaz; okurun keşfedeceği tarihsel bir bağ olarak bırakılır."
        ),
        "muhammed-atalay": (
            "Muhammed Atalay, Oğuz'un on bir yaşındaki küçük kardeşidir. Oyun oynamayı ve televizyon izlemeyi sever; hareketli tavrı evin gündelik sesini ve neşesini oluşturur. Ağabeyine hayranlık duyar ve onunla vakit geçirmek ister. Büyüklerin siyasî veya meslekî meselelerinden çok kendi çocukluk dünyasına yakındır.\n\nMuhammed'in hikâyedeki önemi, Oğuz'un yalnızca idealler veya devlet meseleleri için değil, ailesinin sıradan hayatını korumak için de mücadele ettiğini hatırlatmasıdır. Sınıf arkadaşı olan Muhammed Mete ile karıştırılmamalıdır."
        ),
        "meliha-atalay": (
            "Meliha, Atalay ailesinin dokuz yaşındaki en küçük çocuğudur. Ağabeyleri Muhammed ve Oğuz'un arasında büyür; evin hareketli gündelik hayatına neşe katar. Henüz büyüklerin dünyasındaki siyasî ve meslekî sorunları anlamlandıracak yaşta değildir.\n\nOğuz için Meliha, evin korunması gereken sade ve güvenli tarafını temsil eder. Onun çocukça merakı ve aile içindeki varlığı, Oğuz'un dış dünyadaki gerilimlerden bağımsız olarak önem verdiği hayatı görünür kılar."
        ),
        "alperen-keser": (
            "Alperen Keser, Atatürk'ün 10 Kasım 1938'deki vefatından sonra 29 Kasım 1938'de yönetimi devralan asker ve devlet adamıdır. Merkezî devlet yapısını güçlendirmeyi, sanayileşmeyi hızlandırmayı ve askerî hazırlığı artırmayı hedefler. Türkiye'nin savaş yıllarındaki yönelişinde ve daha sonra Büyük Türk İmparatorluğu'na dönüşecek devlet anlayışının oluşmasında belirleyici rol oynar.\n\nDisiplinli, kararlı ve milliyetçi bir yönetici olarak güçlü devlet fikrini siyasetin merkezine yerleştirir. Bu program devleti hızla güçlendirirken otoriter yönetim biçiminin, güvenlikçi politikaların ve savaş yıllarındaki ağır kararların da temelini oluşturur. Ölüm yılı Vault'ta türetilmiş karar olarak işaretlendiği için bu tanıtımda kesin tarih verilmez."
        ),
        "ismail-karaslan": (
            "İsmail Karaslan, Alperen Keser'den sonra devletin merkezî yönetimini sürdüren asker kökenli devlet adamıdır. Disiplinli, temkinli ve kurumların devamlılığına önem veren bir yönetici olarak tanımlanır. Onunla ilişkilendirilen dönem, yeni genişlemelerden çok mevcut imparatorluk yapısının yerleşmesi, eğitim düzeninin yayılması ve idarenin sağlamlaştırılmasıyla anılır.\n\nBu dönem, dışarıya doğru büyümenin ardından devletin kendi iç işleyişini düzenlemeye çalıştığı bir geçiş evresidir. Karaslan'ın görev süresinin kesin tarihleri Vault'ta türetilmiş olarak işaretlendiğinden, kamuya açık tanıtımda yalnızca Alperen sonrasındaki liderlik konumu belirtilir."
        ),
        "selim-arkan": (
            "Selim Arkan, 1985 yılında Büyük Türk İmparatorluğu'nun Ulu Hanı ve Ankara'daki merkezî yönetimin başındaki isimdir. Teknik ve bürokratik kökeni, onu askerî çevrelerin alışık olduğu gösterişli komuta tarzından ayırır. Karar vermeden önce farklı değerlendirmeleri dinler; ardından kısa ve kesin emirler verir. Yetkisi geniş olsa da imparatorluğun her bölgesini tek tek yönetemeyeceğini, bürokrasinin kararları geciktirebileceğini bilir.\n\nDevletin güçlü ve disiplinli kalmasını ister. Bununla birlikte geçmişte işlenmiş devlet suçlarının gelecekte ağır bir siyasî ve ahlakî borç olarak geri dönebileceğinin farkındadır. Reich kaynaklı bir krizin, imparatorluk hazırlıksızken patlaması en büyük kaygılarındandır. Selim'in soğukkanlı görünüşünün altında, devletin geleceği ve kendi yönetiminin sınırları hakkında sürekli hesap yapan bir hükümdar bulunur."
        ),
        "kaan-demirsoy": (
            "Kaan Demirsoy, Ulu Han'ın kararlarını bağlayıcı devlet emirlerine dönüştüren Başbuyruk makamını yürütür. Kararnamelerin hazırlanması, resmî metinlerin geçerliliği ve merkezî emirlerin doğru biçimde kayda geçirilmesi onun sorumluluğundadır. Bu nedenle devlet içinde yalnızca yazan değil, hangi metnin hüküm taşıdığını bilen kişidir.\n\nSessiz, sabırlı ve titizdir. İnsanlarla arasına mesafe koyar; konuştuğunda konuyu maddeler hâlinde ele alır. Sabiha Erten'le birlikte kararname nüshalarını ve gizli tutanakları takip eder. Kayıtların güvenilirliği onun için bürokratik bir ayrıntı değil, devletin hafızasının temelidir."
        ),
        "sabiha-erten": (
            "Sabiha Erten, Başbuyruk Kalemi'nde kararname sürümlerini, mühür sırasını ve gizli toplantı tutanaklarını takip eder. Bir kararın alınmış olması kadar, hangi metinle ve hangi tarihte yürürlüğe girdiğinin doğru kaydedilmesi de önemlidir. Bu ayrıntılar üzerindeki dikkati, onu devletin belge düzeninde vazgeçilmez kılar.\n\nSessiz ve titizdir; ancak kuruma bağlılığı kör itaat anlamına gelmez. Bir mührün veya belgenin tutarsız olduğunu fark ettiğinde bunu dile getirebilir. Kimin ne zaman neyi imzaladığını bilmesi, onu hem güvenilir bir bürokrat hem de önemli bir tanık hâline getirir."
        ),
        "mete-kutlu": (
            "Mete Kutlu, İmparatorluk İstihbarat Başkanı olarak dış ve stratejik istihbarat alanını, özellikle Reich masasıyla ilgili çalışmaları yönetir. Yabancı temsilcilikler, diplomatik temaslar ve devlet adına yürütülen hassas bilgi ilişkileri onun sorumluluk alanındadır. Bilgi toplamak kadar, hangi bilginin kime ve ne zaman aktarılacağını belirlemek de görevinin parçasıdır.\n\nSakin ve ölçülü konuşur; karşısındakini acele ettirmeden dinler. Korku yaratmaya çalışmaz, fakat bildiklerinin bir kısmını sakladığını hissettirir. Kendi teşkilatının içinde de denetlendiğinin farkındadır. Bu nedenle istihbarat dünyasında güven ve şüpheyi aynı anda yönetmek zorundadır."
        ),
        "rana-tozun": (
            "Rana Tözün, imparatorluğun bilim ve gök araştırmaları alanındaki üst yöneticisidir. Gök Kutup, sensör sistemleri ve üniversitelerle yürütülen araştırma programları onun çalışma alanına girer. Bilimsel sonuçların kişisel kanaatle değil, gözlem ve ölçümle desteklenmesi gerektiğine inanır.\n\nGenç araştırmacılara karşı koruyucu, bürokratik engellere karşı serttir. Verilerin açıklayamadığı bir durumla karşılaştığında acele bir sonuca varmak yerine ölçümleri yeniden incelemeyi tercih eder. Bu yaklaşım onu hem bilimsel titizliğin hem de araştırmanın doğurabileceği bilinmezlik karşısındaki kaygının temsilcisi yapar."
        ),
        "ziya-arat": (
            "Ziya Arat, Maarif ve Gençlik Nazırı olarak mekteplerin, müfredatın ve imparatorluk genelindeki Kanat sisteminin işleyişinden sorumludur. Öğrenci temsil mekanizmaları, okullar arası yarışmalar ve gençlerin ileride yönlendirileceği akademi ve kurumlar da onun görev alanına girer. Bu nedenle okullardaki gelişmeleri yalnızca eğitim meselesi olarak değil, devletin gelecekteki insan kaynağını ilgilendiren bir konu olarak görür.\n\nEnerjik ve ikna edicidir. Canlı konuşma tarzı, taşıdığı makamın denetim gücünü bazen olduğundan hafif gösterebilir. Oysa hangi öğrencinin hangi imkâna erişeceği ve hangi kurumun gençlik çevresinde ne ölçüde etkili olacağı onun sorumluluğundadır."
        ),
        "haluk-sancar": (
            "Haluk Sancar, imparatorluğun Afrika Umumi Valisi olarak geniş bir coğrafyadaki idarî düzenin sorumluluğunu taşır. Raporlarında eğitim, sağlık ve vergi reformlarını öne çıkarır; ancak taşradaki bazı yöneticilerin keyfî uygulamaları, merkezde ilan edilen ilkelerle sahadaki gerçeklik arasında ciddi bir mesafe doğurur. Sancar bu çelişkinin farkındadır.\n\nEnerjik ve ikna edici bir yöneticidir; fakat reformu hızlandırmak yerel güç odaklarıyla çatışma yaratırken mevcut düzeni korumak halkın devlete duyduğu güveni zedeler. Bu nedenle onun görevi yalnızca emir vermek değil, imparatorluğun uzak bölgelerinde yönetim ile sorumluluk arasındaki farkla yüzleşmektir."
        ),
        "reinhard-falkenhorst": (
            "Reinhard Falkenhorst, 1985 yılında Großdeutsches Reich'ın Führer und Reichskanzler makamındadır. Parti, SS, ordu ve sanayi arasındaki rekabeti birbirine karşı dengeleyerek merkezî otoriteyi korur. Bu yöntem rejimin devamını sağlarken karar alma süreçlerini ağırlaştırır.\n\nAğır ve soğuk konuşur; kelimelerini seçerek kullanır. İnsanlardan çok dosyalara ve kayıtlara güvenir. Kendi liderlik mitini korumak zorunda olduğu için hata kabul etmekte zorlanır. Reich'ın Türkiye ile ilişkilerinde teknoloji rekabetini ve savaş sonrası düzenin devamını yakından izler."
        ),
        "martin-kessler": (
            "Martin Kessler, Führer yardımcısı ve Parti Kanzelleyi Başkanı olarak üst düzey atamaları, parti disiplinini ve kurumlar arası siyasî dengeyi yönetir. Ordu ile SS arasındaki rekabette arabulucu rolü üstlenmesi, ona resmî unvanının ötesinde geniş bir nüfuz sağlar.\n\nİlk bakışta nazik ve sıcak görünür; insanların adlarını ve aile bağlarını hatırlaması, görüşmelerde güven kurmasına yardımcı olur. Ancak bu yakınlık her zaman samimiyet değildir. Kessler ideolojik coşkudan çok rejimin devamlılığına ve Führer sonrası iktidar dengesine odaklanır."
        ),
        "ulrich-von-havel": (
            "Ulrich von Havel, Reich Dışişleri Bakanı olarak Türkiye ile yürütülen diplomatik temaslarda Reich'ın çıkarlarını gözetir. Açık çatışma yerine pazarlık, nüfuz ve karşılıklı bağımlılık araçlarını kullanır. Türk tarafını küçümsememesi, onu daha dikkatli bir muhatap hâline getirir.\n\nKonuşması nazik ve ölçülüdür; ancak sunduğu her teklifin içinde bir koşul bulunur. Nezaketi, karşı tarafın hareket alanını daraltan diplomatik hesabın bir parçasıdır. Kişisel duygulardan çok sonuçları ve güç dengesini önemser."
        ),
        "friedrich-wulfhart": (
            "Friedrich Wulfhart, Reichsführer-SS ve Reich güvenlik teşkilatının başıdır. SS'nin, siyasî güvenliğin ve rejimin iç denetim düzeninin en üst sorumlularındandır. Nazi ideolojisine katı biçimde bağlıdır; uygulamada ise farklı kurumları birbirine karşı kullanabilecek kadar hesaplıdır.\n\nBağırarak otorite kurmaz. Soru sorar, cevapları bekler ve ayrıntıları kayda geçirir. Onun temsil ettiği Reich düzeninde gözetim ve baskı, istisna değil yönetim anlayışının temel parçalarıdır."
        ),
        "konrad-weissmann": (
            "Konrad Weissmann, Reich'ın yüksek enerji fiziği ve özel teknoloji programlarında çalışan baş nükleer fizikçidir; SFA-P Polaris'teki araştırmaların bilimsel yüzlerinden biridir. İnsan ilişkilerinden çok ölçümlere ve sonuçlara önem verir. Kibirli ve sabırsız tavrı, çevresindekilerle mesafe yaratır.\n\nWeissmann bilinmeyen bir olguyu yalnızca açıklamakla yetinmek istemez; ondan yararlanma ihtimaline de yönelir. Bilimsel merak ile siyasî ve askerî güç arzusunun birbirine karışması, onu Türk bilim çevrelerinin daha temkinli yaklaşımından ayırır."
        )
    }
    for key, description in expansions.items():
        record = main_nodes.get(key) or political_nodes.get(key) or state_nodes.get(key) or reich_nodes.get(key)
        if record:
            record["content"] += "\n\n## Karakterin yapısı ve hikâyedeki yeri\n\n" + description

    def collect(keys, source):
        return [source[key] for key in keys if key in source]

    young_people = make_character_group(
        "Genç karakterler", "GENÇ KARAKTERLER",
        "1985 yılında iki İstanbul mektebinde öğrenim gören, farklı hedefleri ve yönetim anlayışlarıyla birbirine bağlanan genç kuşak.",
        [
            make_character_group(
                "Üsküdar Milli İlim ve İrfan Mektebi", "ÜSKÜDAR MEKTEBİ",
                "Oğuz, Alper, İsmail, Muhammed Mete, Aylin ve Alev'in bulunduğu okul çevresi.",
                collect(["oguz-kagan-atalay","alper-ulac-altayli","ismail-yagiz-aslan","muhammed-mete","aylin-aksoy","alev-acar"], main_nodes),
                "uskudar-students"
            ),
            make_character_group(
                "İstanbul Şarkın İlim ve Teknoloji Mektebi", "ŞARKIN MEKTEBİ",
                "Tomris ve Asena'nın temsil ettiği, Üsküdar çevresiyle görev ve rekabet ilişkileri bulunan okul.",
                collect(["tomris-ilter","asena-korkut"], main_nodes),
                "sarkin-students"
            )
        ],
        "young-characters"
    )

    atalay_suyu = make_character_group(
        "Atalay Soyu", "AİLE AĞACI",
        "Atalay ailesinin kuşakları ve aileyle bağlantılı Kaya ailesi.",
        [
            make_character_group(
                "Atalay büyükleri", "KUŞAK I",
                "Atalay ailesinin büyükleri.",
                collect(["nec-det-atalay","sabiha-atalay"], main_nodes),
                "atalay-elders"
            ),
            make_character_group(
                "Kaya ailesi", "AİLE BAĞI",
                "Atalay ailesiyle bağlantılı Kaya ailesi.",
                collect(["riza-kaya","naciye-kaya","aysel-atalay"], main_nodes),
                "kaya-branch"
            ),
            make_character_group(
                "Cengiz Atalay kuşağı", "KUŞAK II",
                "Atalay ailesinin mühendislik geleneğiyle tanınan kuşağı.",
                collect(["cengiz-atalay"], main_nodes),
                "atalay-second-generation"
            ),
            make_character_group(
                "Oğuz, Muhammed ve Meliha", "KUŞAK III",
                "Atalay ailesinin genç kuşağı.",
                collect(["oguz-kagan-atalay","muhammed-atalay","meliha-atalay"], main_nodes),
                "atalay-third-generation"
            ),
        ],
        "atalay-lineage"
    )

    keser_soyu = make_character_group(
        "Keser Soyu", "AİLE AĞACI",
        "Keser ailesinin bilinen kuşakları; isimler aile ağacında ortak soy adıyla standartlaştırılmıştır.",
        [
            make_character_group(
                "İlk kuşak", "KUŞAK I",
                "Keser soyunun bilinen eski kuşağı.",
                collect(["abdullah-keser"], political_nodes),
                "keser-first-generation"
            ),
            make_character_group(
                "İkinci kuşak", "KUŞAK II",
                "Oğuz ve Gül'ün kuşağı.",
                collect(["oguz-keser","gul-keser"], political_nodes),
                "keser-second-generation"
            ),
            make_character_group(
                "Üçüncü kuşak", "KUŞAK III",
                "Kaan, Ali ve Firuze'nin kuşağı.",
                collect(["kaan-keser","ali-keser","firuze-keser"], political_nodes),
                "keser-third-generation"
            ),
            make_character_group(
                "Dördüncü kuşak", "KUŞAK IV",
                "Alperen Keser'in kuşağı.",
                collect(["alperen-keser"], political_nodes),
                "keser-fourth-generation"
            ),
        ],
        "keser-lineage"
    )

    state_leaders = make_character_group(
        "Büyük Türk İmparatorluğu yönetimi", "TÜRK DEVLET KADROSU",
        "Ulu Hanlık, merkezî bürokrasi, istihbarat, bilim, eğitim ve taşra yönetiminde görev alan kişiler.",
        [
            make_character_group(
                "Ulu Hanlar ve devlet başkanları", "YÖNETİM ZİNCİRİ",
                "İmparatorluğun yakın dönem liderleri.",
                collect(["alperen-keser","ismail-karaslan","selim-arkan"], political_nodes),
                "turkish-rulers"
            ),
            make_character_group(
                "Merkezî yönetim ve kurumlar", "DEVLET KADROSU",
                "Başbuyruk Kalemi, istihbarat, bilim, eğitim ve taşra yönetiminin üst düzey isimleri.",
                collect(["kaan-demirsoy","sabiha-erten","mete-kutlu","rana-tozun","ziya-arat","haluk-sancar"], state_nodes),
                "turkish-state-cadre"
            )
        ],
        "state-leaders"
    )

    reich_leadership = make_character_group(
        "Großdeutsches Reich yönetimi", "REICH KADROSU",
        "Reich'ın parti, dış politika, güvenlik ve bilim alanlarındaki önde gelen yöneticileri.",
        collect(["reinhard-falkenhorst","martin-kessler","ulrich-von-havel","friedrich-wulfhart","konrad-weissmann"], reich_nodes),
        "reich-leadership"
    )

    roots = [young_people, atalay_suyu, keser_soyu, state_leaders, reich_leadership]
    roots = [item for item in roots if item.get("children")]
    if not roots:
        return None

    return {
        "id":"characters",
        "title":"Karakterler",
        "description":"Genç kuşak, Atalay ve Keser aileleri, imparatorluk yönetimi ve Reich kadrosu. Karakterlerin görevleri, hedefleri, kişilikleri ve birbirleriyle ilişkileri birlikte ele alınır.",
        "view":"tree",
        "label":"KARAKTER VE SOY AĞAÇLARI",
        "order":3,
        "nodes":roots
    }


def read_public_archive_note(path, archive_root):
    """Read an archive document only when status and visibility are explicitly approved/public."""
    if not path.is_file() or path.suffix.lower() not in {".md", ".txt"}:
        return None
    raw = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    if not raw.startswith("---\n"):
        return None
    end = raw.find("\n---", 4)
    if end < 0:
        return None

    metadata = {}
    for line in raw[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        metadata[key.strip().lower()] = value

    status = normalize(metadata.get("status", ""))
    visibility = normalize(metadata.get("visibility", metadata.get("publication", metadata.get("yayın", ""))))
    if status not in {"onaylandi", "approved", "established canon"}:
        return None
    if visibility not in {"public", "kamuya acik", "herkese acik"}:
        return None

    restricted = normalize(" ".join([
        metadata.get("tags", ""),
        metadata.get("privacy", ""),
        metadata.get("gizlilik", ""),
    ]))
    blocked = ("taslak", "draft", "proposed", "gizli", "classified", "internal",
               "private", "confidential", "unlisted", "spoiler")
    if any(term in restricted for term in blocked):
        return None

    body = raw[end + 4:].lstrip("\n")
    lines = body.splitlines()
    title = metadata.get("title", "").strip()
    if not title and path.suffix.lower() == ".txt":
        first = next((i for i, line in enumerate(lines) if line.strip()), None)
        if first is not None:
            title = lines[first].strip().lstrip("#").strip()
            lines.pop(first)
    if not title:
        for index, line in enumerate(lines):
            match = re.match(r"^#\s+(.+)$", line.strip())
            if match:
                title = match.group(1).strip()
                lines.pop(index)
                break
    if not title:
        title = path.parent.name if path.name.lower() in {"index.md", "index.txt"} else path.stem

    content = "\n".join(lines).strip()
    summary = metadata.get("summary", "").strip()
    if not summary:
        for paragraph in re.split(r"\n\s*\n", content):
            candidate = paragraph.strip()
            if candidate:
                summary = re.sub(r"[*_>#]", "", candidate)[:240]
                break
    aliases = []
    raw_aliases = metadata.get("aliases", "").strip()
    if raw_aliases.startswith("[") and raw_aliases.endswith("]"):
        aliases = [item.strip().strip("'\"") for item in raw_aliases[1:-1].split(",") if item.strip()]
    try:
        order = int(metadata.get("order", 999))
    except (TypeError, ValueError):
        order = 999

    return {
        "title": title,
        "summary": summary,
        "content": content,
        "aliases": aliases,
        "sourceName": path.stem,
        "path": path.relative_to(archive_root).as_posix(),
        "date": str(metadata.get("date", metadata.get("period", ""))).strip(),
        "order": order,
        "country": normalize_country(metadata.get("country", metadata.get("ülke", ""))),
        "character": metadata.get("character", "").strip(),
        "character_group": metadata.get("character_group", "").strip(),
        "record_type": metadata.get("record_type", "").strip(),
        "theme": metadata.get("theme", "").strip(),
    }


def scan_public_archive_nodes(directory, archive_root, category, excluded=None):
    """Preserve folder/index hierarchy while excluding every unapproved document."""
    if not directory.is_dir():
        return []
    excluded = excluded or set()
    entries = sorted(directory.iterdir(), key=lambda item: item.name.casefold())
    records = []
    paired_directories = set()

    for entry in entries:
        if not entry.is_file() or entry.resolve() in excluded:
            continue
        if entry.suffix.lower() not in {".md", ".txt"} or entry.name.lower() in {"readme.md", "index.md", "index.txt"}:
            continue
        doc = read_public_archive_note(entry, archive_root)
        if not doc:
            continue
        paired = directory / entry.stem
        children = scan_public_archive_nodes(paired, archive_root, category) if paired.is_dir() else []
        if paired.is_dir():
            paired_directories.add(paired.resolve())
        record = node(category, doc, doc.get("date", ""))
        record["order"] = doc.get("order", 999)
        record["children"] = children
        records.append(record)

    for entry in entries:
        if not entry.is_dir() or entry.resolve() in paired_directories:
            continue
        index_file = next((entry / name for name in ("index.md", "index.txt") if (entry / name).is_file()), None)
        if index_file:
            child_nodes = scan_public_archive_nodes(entry, archive_root, category, {index_file.resolve()})
            doc = read_public_archive_note(index_file, archive_root)
            if doc:
                record = node(category, doc, doc.get("date", ""))
                record["order"] = doc.get("order", 999)
                record["children"] = child_nodes
                records.append(record)
            else:
                records.extend(child_nodes)
        else:
            records.extend(scan_public_archive_nodes(entry, archive_root, category))

    return sorted(records, key=lambda item: (item.get("order", 999), item["title"].casefold()))


def public_folder_nodes(category, relative_folder):
    """Import only explicitly approved, public Markdown notes from an Obsidian author folder."""
    folder = VAULT / relative_folder
    if not folder.is_dir():
        return []
    records = []
    for path in sorted(folder.rglob("*.md"), key=lambda item: item.as_posix().casefold()):
        if path.name.casefold() in {"readme.md", "index.md"}:
            continue
        doc = read_public_archive_note(path, VAULT)
        if doc:
            record = node(category, doc, str(doc.get("date", "")))
            record["order"] = doc.get("order", 999)
            records.append(record)
    return records

def import_institutions():
    specs = [
        "Kuruluşlar/Hilalifiyet Merkezi - İstanbul.md",
    ]
    records = []
    for rel in specs:
        doc = read_doc(rel)
        if doc:
            records.append(node("institutions", doc))
    records += public_folder_nodes("institutions", "Kuruluşlar/Kamuya Açık")
    apply_default_leaf_country(records, "turkish")
    return {
        "id":"institutions",
        "title":"Kurumlar",
        "description":"Kamuya açık kurumsal kayıtlar. Taslak, öneri veya gizli dosyalar bu kataloğa aktarılmaz.",
        "view":"catalogue",
        "label":"KURUM DOSYALARI",
        "order":4,
        "nodes":records
    }

def import_geography():
    base = "Alternatif Tarih/Dünya/"
    specs = [
        (base + "Genel Dünya.md", "1985 · DÜNYA DÜZENİ"),
        (base + "Dünya Paylaşımı 1946.md", "1946 · SİYASİ PAYLAŞIM"),
        (base + "Türkiye.md", "DEVLET DOSYASI"),
        (base + "Almanya.md", "DEVLET DOSYASI"),
        (base + "Amerika.md", "DEVLET DOSYASI"),
        (base + "Diğer Devletler.md", "DİĞER GÜÇLER"),
    ]
    records = []
    for rel, date in specs:
        doc = read_doc(rel)
        if doc:
            records.append(node("geography", doc, date))
    records += public_folder_nodes("geography", "Alternatif Tarih/Dünya/Coğrafya")
    return {
        "id":"geography",
        "title":"Dünya Atlası",
        "description":"1985 dünya düzeni, 1946 paylaşımı, ülke profilleri ve şehir/tarih kayıtları. Kesin sınır çizgileri ve ulaşım katmanları kaynak geldikçe genişler.",
        "view":"catalogue",
        "label":"COĞRAFYA VE SİYASİ ATLAS",
        "order":2,
        "nodes":records
    }

def _merge_public_records(existing, public_records):
    """Prefer a detailed approved public profile over an older short alias record."""
    public_keys = set()
    for record in public_records:
        for value in [record.get("title", ""), record.get("sourceName", "")] + record.get("aliases", []):
            if value:
                public_keys.add(normalize(value))
    kept = []
    for record in existing:
        values = [record.get("title", ""), record.get("sourceName", "")] + record.get("aliases", [])
        if any(normalize(value) in public_keys for value in values if value):
            continue
        kept.append(record)
    return kept + public_records


def import_technology():
    technology_root = ROOT / "content" / "archives" / "technology"
    existing = scan_public_archive_nodes(technology_root, technology_root, "technology")
    public_records = public_folder_nodes("technology", "Alternatif Tarih/Teknoloji/Kamuya Açık")
    records = _merge_public_records(existing, public_records)
    apply_default_leaf_country(records, "turkish")
    return {
        "id":"technology",
        "title":"Teknoloji",
        "description":"TA-85 Gökkanat ve diğer projelere ait yalnızca onaylanmış, genel ve tarihsel teknoloji kayıtları.",
        "view":"catalogue",
        "label":"TEKNOLOJİ KATALOĞU",
        "order":5,
        "nodes":records
    }

def import_society():
    specs = [
        ("Aslı Olan Düzen/B-3/B-3 Sınıf Profili.md", "1985 · EĞİTİM"),
        ("Aslı Olan Düzen/Eğitim Sistemi Analizi.md", "1985 · EĞİTİM"),
        ("Aslı Olan Düzen/World/Politics/Kanat.md", "İMPARATORLUK GENELİ"),
    ]
    records = []
    for rel, date in specs:
        doc = read_doc(rel)
        if not doc:
            continue
        doc["content"] = "\n".join(
            line for line in doc["content"].splitlines()
            if not re.search(r"BELİRLENMESİ GEREKİYOR|YAZAR ONAYI BEKLİYOR", line, re.I)
        )
        records.append(node("society", doc, date))
    schedule = read_doc("Aslı Olan Düzen/B-3/B-3 Ders Programı.md")
    if schedule:
        schedule["title"] = "B-3 — Haftalık Ders Düzeni"
        schedule["summary"] = "1985 eğitim yılında B-3 sınıfı için kayda alınmış haftalık ders akışı."
        schedule["content"] = """B-3 programı haftada beş güne ve toplam kırk ders saatine yayılır. Her gün sekiz ders bulunur; ilk ders 09.00'da başlar, son ders 17.40'ta tamamlanır.

## Günlük zaman düzeni
- Ders süresi: 40 dakika.
- Normal teneffüsler: 20 dakika.
- Öğle arası: 1 saat 20 dakika.
- Günlük ders süresi: 320 dakika.

## Ders alanları
Türk Dili ve Edebiyatı, Matematik, Fizik, Kimya, Biyoloji, Tarih, Coğrafya, Yabancı Dil, Felsefe ve Mantık, Toplum ve Yurttaşlık, Teknoloji ve Tasarım, Beden Eğitimi, Sosyolojik Eğitim, Sanat ve Kültür.

Bu kayıt yalnızca B-3 sınıfının programını gösterir; okulun tüm sınıflarına ait ortak çizelge değildir."""
        records.append(node("society", schedule, "1985 · HAFTALIK PROGRAM"))
    public_records = public_folder_nodes("society", "Aslı Olan Düzen/Toplum ve Gündelik Hayat")
    records = _merge_public_records(records, public_records)
    for record in records:
        record_path = normalize(record.get("path", ""))
        if record_path == "kanat" or "kanat sistemi" in normalize(record.get("title", "")):
            record["country"] = "both"
    apply_default_leaf_country(records, "turkish")
    return {
        "id":"society",
        "title":"Toplum ve Gündelik Hayat",
        "description":"Okul profili, B-3 haftalık programı ve Kanat sisteminin bilinen kamusal çerçevesi. Genel gündelik yaşam ve ekonomi kayıtları ayrıca hazırlanmalıdır.",
        "view":"catalogue",
        "label":"TOPLUMSAL YAŞAM KAYITLARI",
        "order":6,
        "nodes":records
    }

def import_media():
    records = []
    source = read_doc("Tarihi Olaylar/Olaylar/10 KASIM 1940.md")
    if source:
        press_doc = {
            "title":"10 Kasım 1940 — Ankara Ziyareti ve Dünya Basını",
            "summary":"Ankara ziyareti, Anıtkabir töreni ve olayın Amerikan basınında yarattığı yankıya ilişkin mevcut kronoloji notlarından derlenen basın bağlamı.",
            "content":"""10 Kasım 1940 tarihli kronoloji kaydı, Adolf Hitler'in Ankara'ya gelişi ve Anıtkabir ziyaretinin Türk kamuoyunda ve uluslararası basında yankı bulduğunu belirtir.

## Mevcut kayıt
Kanon notunda Amerikan basınının ziyareti, Avrupa'daki güç dengesinin değiştiğine dair bir uyarı işareti olarak değerlendirdiği aktarılır. Bu arşiv girdisi, söz konusu bilgiyi kataloglar; henüz özgün gazete nüshası, yayın adı, muhabir, sayfa numarası veya tam metin mevcut değildir.

## Bağlantılı kayıt
[[10 KASIM 1940]]

## Dosya durumu
Site malzemeleri arasında Ankara ziyareti haberine ayrılmış bir görsel dosya bulunur. Görselin yayın künyesi ve özgün kaynağı ayrıca tamamlanmalıdır."""
        }
        press_doc["sourceName"] = "10 KASIM 1940"
        press_doc["path"] = source["path"]
        press_doc["aliases"] = ["Ankara ziyareti basını", "Dünya basını"]
        press_doc["country"] = "both"
        records.append(node("media", press_doc, "10 KASIM 1940"))
    records += public_folder_nodes("media", "Medya ve Basın")
    apply_default_leaf_country(records, "both")
    return {
        "id":"media",
        "title":"Basın ve Yayın Arşivi",
        "description":"Basın yansımaları ve yayın kayıtları. Mevcut tarih notlarının ötesindeki gazete nüshaları, yayın akışları ve künye bilgileri henüz hazırlanmayı bekliyor.",
        "view":"catalogue",
        "label":"BASIN VE YAYIN KAYITLARI",
        "order":7,
        "nodes":records
    }

def import_documents():
    records = public_folder_nodes("documents", "Belge Arşivi")
    apply_default_leaf_country(records, "both")
    return {
        "id":"documents",
        "title":"Belge Arşivi",
        "description":"Kamuya açık resmî kararlar, yazışmalar, toplantı tutanakları ve tarihî dosyalar. Yayımlanmaya onaylanmış belgeler eklendikçe katalog dolar.",
        "view":"catalogue",
        "label":"BELGE VE EVRAK KATALOĞU",
        "order":8,
        "nodes":records
    }

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
    for cat in categories:
        resolve(cat.get("nodes", []))

    def clear_unpublished_links(nodes):
        for n in nodes:
            def replace_link(match):
                target = normalize(match.group(1))
                if target not in index:
                    return match.group(2) or match.group(1)
                return match.group(0)
            n["content"] = WIKILINK.sub(replace_link, n.get("content", ""))
            clear_unpublished_links(n.get("children", []))

    for cat in categories:
        clear_unpublished_links(cat.get("nodes", []))


def inherit_archive_context(nodes, inherited=None):
    """Propagate character, archive type, theme and country through nested records."""
    fields = ("country", "character", "character_group", "record_type", "theme")
    inherited = inherited or {}
    for item in nodes or []:
        context = dict(inherited)
        for field in fields:
            value = item.get(field) or context.get(field)
            if value:
                item[field] = value
                context[field] = value
        inherit_archive_context(item.get("children", []), context)

def manual_categories():
    """Discover extra archive units without publishing unapproved documents."""
    root = ROOT / "content" / "archives"
    categories = []
    reserved = {"chronology", "world", "characters", "institutions", "technology", "geography", "society", "media", "documents"}
    if not root.is_dir():
        return categories

    for folder in sorted(root.iterdir(), key=lambda item: item.name.casefold()):
        if not folder.is_dir() or folder.name in reserved or folder.name.startswith("_"):
            continue
        config_file = folder / "_archive.json"
        cfg = json.loads(config_file.read_text(encoding="utf-8")) if config_file.is_file() else {
            "title": folder.name.title(), "view": "tree", "order": 99
        }
        records = scan_public_archive_nodes(folder, folder, folder.name)
        inherit_archive_context(records)
        if not records:
            continue
        view = cfg.get("view", "tree")
        if view not in {"tree", "catalogue"}:
            view = "tree"
        categories.append({
            "id": folder.name,
            "title": cfg.get("title", folder.name.title()),
            "description": cfg.get("description", ""),
            "view": view,
            "label": cfg.get("label", "ARŞİV"),
            "order": cfg.get("order", 99),
            "nodes": records,
        })
    return categories

def flatten(nodes):
    out=[]
    for n in nodes:
        out.append(n)
        out.extend(flatten(n.get("children",[])))
    return out

def discover_archives():
    cats=[]
    for fn in [import_chronology,import_geography,import_characters,import_institutions,import_technology,import_society,import_media,import_documents]:
        cat=fn()
        if cat: cats.append(cat)
    cats += manual_categories()
    cats.sort(key=lambda c:(c.get("order",99),c["title"].casefold()))
    attach_links(cats)
    return {"categories":cats}

def build():
    """Compatibility entry point that delegates to the complete site builder."""
    import build_site
    build_site.build()


if __name__ == "__main__":
    build()
