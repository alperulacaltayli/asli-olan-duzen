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
    # A period such as "Ocak-Mart 1942" belongs at the end of its
    # stated range, not at the beginning of January before later events.
    range_match = re.search(r"\b("+pat+r")\s*[-–]\s*("+pat+r")\s+(19\d{2}|20\d{2})\b", text)
    range_label = ""
    if range_match:
        start_name, end_name = range_match.group(1), range_match.group(2)
        year = int(range_match.group(3))
        month = MONTHS[end_name]
        day = 31
        tr={1:"Ocak",2:"Şubat",3:"Mart",4:"Nisan",5:"Mayıs",6:"Haziran",7:"Temmuz",8:"Ağustos",9:"Eylül",10:"Ekim",11:"Kasım",12:"Aralık"}
        range_label = f"{tr[MONTHS[start_name]]}-{tr[month]} {year}"
    else:
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
    if range_label: label = range_label
    elif year and month and day: label=f"{day} {tr[month]} {year}"
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
    # Only approved, reader-facing dates are added to the public chronology.
    public_milestones = [
        {
            "year":1985, "month":9, "day":10, "date":"10 Eylül 1985",
            "title":"10 Eylül 1985 — Alman Teknik Heyetinin İstanbul Ziyareti",
            "path":"Tarihi Olaylar/1985 Alman Heyeti.md",
            "summary":"Reich heyeti, teknik işbirliği görüntüsü altında Türk havacılık ve sensör kapasitesini değerlendirmek üzere İstanbul'a geldi.",
            "content":"""# 10 Eylül 1985 — Alman Teknik Heyetinin İstanbul Ziyareti

Eylül 1985'te Großdeutsches Reich'tan bir heyet İstanbul'a geldi. Resmî çerçeve teknik temas ve işbirliğiydi; heyetin asıl ilgisi ise Büyük Türk İmparatorluğu'nun havacılık ve sensör alanlarında Reich'la arasındaki teknolojik mesafeyi ne ölçüde kapattığını anlamaktı.

Heyetin İstanbul'daki varlığı, devletler arası rekabetin yalnızca diplomatik görüşmelerde değil, teknik kurumlar ve araştırma çevrelerinde de hissedildiğini gösterdi.

Türk tarafı ziyaretin resmî nezaketini korurken Reich heyetinin temasları dikkatle izleniyordu. Bu ziyaret, 1985 sonbaharında iki imparatorluk arasındaki güvensizliğin görünür hâle geldiği gelişmelerden biridir."""
        },

    ]
    for event in public_milestones:
        if normalize(event["title"]) in seen_titles:
            continue
        doc = {
            "title":event["title"], "summary":event["summary"], "content":event["content"],
            "path":event["path"],
            "sourceName":event["title"], "aliases":[], "country":"turkish"
        }
        rec = node("chronology", doc, event["date"])
        years.setdefault(event["year"], []).append(
            (event["month"],event["day"],event["title"],rec)
        )
        seen_titles.add(normalize(event["title"]))

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

    content = spec.get("profile") or "\n\n".join(fields)
    summary = spec.get("summary") or spec.get("personality", "")
    return {
        "id": category + "-" + slug(spec["key"]),
        "path": spec.get("path", "03_KARAKTERLER/" + spec["name"] + ".md"),
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
            "personality":"Neşeli, konuşkan, uyumlu ve çözüm odaklı.",
            "aliases":["Alev Acar"]
        },
        {
            "key":"asena-korkut", "path":main_base+"Asena Korkut.md", "name":"Asena Korkut",
            "date":"1968 · 17 yaş", "birth":"1968", "age":"17",
            "role":"Öğrenci · 5. Kanat · Şarkın Mektebi başkan yardımcısı · saha istihbaratı hedefi",
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
            "role":"Öğrenci · 6. Kanat · Şarkın Mektebi okul başkanı · millî istihbarat ve askerî güvenlik hedefi",
            "appearance":"Uzun siyah saçlı ve koyu gözlü.",
            "personality":"Kendine güvenen, ciddi, kararlı ve yönetici yönü güçlü.",
            "aliases":["Tomris İlter","TOMRİS İLTER"]
        },
        {
            "key":"ismail-yagiz-aslan", "path":main_base+"İsmail Yağız Aslan.md", "name":"İsmail Yağız Aslan",
            "date":"1968 · 17 yaş", "birth":"1968", "age":"17",
            "role":"Öğrenci · 5. Kanat · Üsküdar Mektebi başkan yardımcısı · siyaset hedefi",
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
            "role":"Öğrenci · 3. Kanat · Üsküdar Mektebi · askerî pilotluk hedefi",
            "appearance":"Dik duruşlu, düzenli ve bakımlı bir görünüme sahiptir.",
            "personality":"Sakin, soğukkanlı, disiplinli, gözlemci ve teknik konulara meraklı.",
            "aliases":["Oğuz Kağan Atalay"]
        },
        {
            "key":"aysel-atalay", "path":main_base+"Aysel Atalay.md", "name":"Aysel Atalay",
            "date":"1947 · 38 yaş", "birth":"1947", "age":"38",
            "role":"Ev hanımı",
            "appearance":"Sade ve zarif bir giyim tarzını tercih eder.",
            "personality":"Sakin, sabırlı, anlayışlı ve koruyucu.",
            "aliases":["Aysel Atalay"]
        },
        {
            "key":"cengiz-atalay", "path":main_base+"Cengiz Atalay.md", "name":"Cengiz Atalay",
            "date":"1945 · 40 yaş", "birth":"1945", "age":"40",
            "role":"Askerî uçak mühendisi · Gökkanat programı",
            "appearance":"Düzenli ve klasik giyinir; resmî ve hafif askerî çizgileri tercih eder.",
            "personality":"Özgüvenli, enerjik, meraklı ve çalışkan.",
            "aliases":["Cengiz Atalay"]
        },
        {
            "key":"meliha-atalay", "path":main_base+"Meliha Atalay.md", "name":"Meliha Atalay",
            "date":"1975 · 10 yaş", "birth":"1975", "age":"10",
            "role":"Öğrenci",
            "appearance":"Yaşına uygun, sade ve rahat kıyafetler tercih eder.",
            "personality":"Çalışkan, kararlı, inatçı ve azimli.",
            "aliases":["Meliha Atalay"]
        },
        {
            "key":"muhammed-atalay", "path":main_base+"Muhammed Atalay.md", "name":"Muhammed Atalay",
            "date":"1973 · 12 yaş", "birth":"1973", "age":"12",
            "role":"Öğrenci · mühendisliğe ilgi duyuyor",
            "appearance":"Yaşına uygun, sade ve rahat giyinir.",
            "personality":"Meraklı, hareketli ve teknik konulara ilgili.",
            "aliases":["Muhammed Atalay"]
        },
        {
            "key":"nec-det-atalay", "path":main_base+"Necdet Atalay.md", "name":"Necdet Atalay",
            "date":"1918 doğumlu", "birth":"1918",
            "role":"Emekli askerî uçak mühendisi",
            "appearance":"Sade, klasik ve düzenli giyinir.",
            "personality":"Ağırbaşlı, disiplinli, otoriter ve az konuşan.",
            "aliases":["Necdet Atalay"]
        },
        {
            "key":"sabiha-atalay", "path":main_base+"Sabiha Atalay.md", "name":"Sabiha Atalay",
            "date":"1923 · 62 yaş", "birth":"1923", "age":"62",
            "role":"Ev hanımı",
            "appearance":"Sade ve klasik kıyafetler tercih eder.",
            "personality":"Sakin, sabırlı, anlayışlı ve aile odaklı.",
            "aliases":["Sabiha Atalay"]
        },
        {
            "key":"naciye-kaya", "path":main_base+"Naciye Kaya.md", "name":"Naciye Kaya",
            "date":"1920 · 65 yaş", "birth":"1920", "age":"65",
            "role":"Ev hanımı",
            "appearance":"Sade ve geleneksel bir giyim tarzına sahiptir.",
            "personality":"Girişken, konuşkan, açık sözlü ve pratik zekâlı.",
            "aliases":["Naciye Kaya"]
        },
        {
            "key":"riza-kaya", "path":main_base+"Rıza Kaya.md", "name":"Rıza Kaya",
            "date":"1916 · 69 yaş", "birth":"1916", "age":"69",
            "role":"Mesleği kaynakta belirtilmemiştir",
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
            "date":"1888 doğumlu · 29 Kasım 1938'de yönetimi devraldı", "birth":"1888 · Giresun, Kuşköy",
            "role":"Asker ve devlet adamı · 1938'de yönetimi devralan lider",
            "personality":"Disiplinli, kararlı, milliyetçi ve sanayileşme yanlısı.",
            "aliases":["Alperen","Alperen Keser"]
        },
        {
            "key":"ismail-karaslan", "path":political_base+"İsmail Karaslan.md", "name":"İsmail Karaslan",
            "date":"1904 doğumlu · 1960–1975 dönemi",
            "birth":"1904 · Hatay",
            "role":"Asker ve devlet adamı",
            "personality":"Disiplinli, devletçi, temkinli ve güçlü merkezi yönetim yanlısı.",
            "aliases":["İsmail Karaslan"]
        },
        {
            "key":"selim-arkan", "path":political_base+"Selim Arkan.md", "name":"Selim Arkan",
            "date":"1935 doğumlu · 1985'te 50 yaşında",
            "birth":"1935 · Ankara",
            "role":"Siyasetçi ve devlet adamı",
            "personality":"Soğukkanlı, pragmatik, devletçi ve stratejik düşünen.",
            "aliases":["Selim Arkan"]
        },
    ]

    extra_student_specs = [
        {
            "key":"alper-ulac-altayli", "path":"Alternatif Tarih/Karakterler/Ana ve Destek Karakterler/Alper Ulaç Altaylı.md", "name":"Alper Ulaç Altaylı",
            "date":"1968 · 17 yaş", "birth":"1968", "age":"17",
            "role":"Öğrenci · 6. Kanat · Üsküdar Milli İlim ve İrfan Mektebi okul başkanı",
            "appearance":"Düzenli, ölçülü ve sade giyinir; bulunduğu ortamda dikkat çekmekten çok kontrolü elinde tutmayı tercih eder.",
            "personality":"Sakin, hesapçı, stratejik ve kontrol ihtiyacı yüksek.",
            "summary":"Üsküdar Mektebi'nin altı kanatlı okul başkanı; sakin, kontrollü ve stratejik düşünmesiyle tanınır.",
            "profile_only":True, "country":"turkish", "aliases":["Alper","Alper Ulaç Altaylı"]
        }
    ]
    state_specs = [
        {
            "key":"kaan-demirsoy", "path":"Alternatif Tarih/Karakterler/Devlet/Kaan Demirsoy.md", "name":"Kaan Demirsoy", "date":"1936 doğumlu",
            "birth":"1936", "role":"Başbuyruk · Ulu Han'ın iradesini bağlayıcı emre dönüştüren makam",
            "personality":"Sessiz, titiz, sabırlı ve kayıt düzenine bağlı.",
            "summary":"İmparatorluk yönetiminin emir, kararname ve kayıt düzenini ayakta tutan Başbuyruk.",
            "profile_only":True, "country":"turkish"
        },
        {
            "key":"sabiha-erten", "path":"Alternatif Tarih/Karakterler/Devlet/Sabiha Erten.md", "name":"Sabiha Erten", "date":"1945 doğumlu · 40 yaş",
            "birth":"1945", "age":"40", "role":"Başbuyruk Kalemi Müsteşarı",
            "personality":"Sessiz, dikkatli, titiz ve gerektiğinde itiraz etmekten çekinmeyen.",
            "summary":"Kararname nüshalarının, mühür sırasının ve gizli tutanakların düzenini takip eden bürokrat.",
            "profile_only":True, "country":"turkish"
        },
        {
            "key":"mete-kutlu", "path":"Alternatif Tarih/Karakterler/Devlet/Mete Kutlu.md", "name":"Mete Kutlu", "date":"1931 doğumlu · 54 yaş",
            "birth":"1931", "age":"54", "role":"İmparatorluk İstihbarat Başkanı",
            "personality":"Sakin, ölçülü, sabırlı ve dikkatli bir dinleyici.",
            "summary":"Dış istihbarat ve Reich masasını yöneten; bildiğini hemen açığa vurmayan istihbarat başkanı.",
            "profile_only":True, "country":"turkish"
        },
        {
            "key":"rana-tozun", "path":"Alternatif Tarih/Karakterler/Devlet/Rana Tözün.md", "name":"Rana Tözün", "date":"1938 doğumlu · 47 yaş",
            "birth":"1938", "age":"47", "role":"Bilim ve Gök Araştırmaları Başkanı",
            "personality":"Sakin, kesin, sabırlı ve veriye bağlı.",
            "summary":"Gök Kutup, sensör çalışmaları ve imparatorluğun bilim programlarından sorumlu üst düzey yönetici.",
            "profile_only":True, "country":"turkish"
        },
        {
            "key":"ziya-arat", "path":"Alternatif Tarih/Karakterler/Devlet/Ziya Arat.md", "name":"Ziya Arat", "date":"1934 doğumlu · 51 yaş",
            "birth":"1934", "age":"51", "role":"Maarif ve Gençlik Nazırı",
            "personality":"Enerjik, ikna edici ve siyasî açıdan dikkatli.",
            "summary":"Mekteplerin, müfredatın ve imparatorluk genelindeki Kanat sisteminin sorumlusu.",
            "profile_only":True, "country":"turkish"
        },
        {
            "key":"haluk-sancar", "path":"Alternatif Tarih/Karakterler/Devlet/Haluk Sancar.md", "name":"Haluk Sancar", "date":"1927 doğumlu · 58 yaş",
            "birth":"1927", "age":"58", "role":"Afrika Umumi Valisi",
            "personality":"Enerjik, konuşkan, ikna edici ve siyasî denge gözeten.",
            "summary":"Afrika'daki reform hedefleri ile taşradaki keyfî uygulamalar arasındaki çelişkinin merkezindeki vali.",
            "profile_only":True, "country":"turkish"
        }
    ]
    teacher_specs = [
        {
            "key":"nihat-karaca", "path":"Alternatif Tarih/Karakterler/Okul/Nihat Karaca.md", "name":"Nihat Karaca", "date":"1985 · Mektep yönetimi",
            "role":"Düzen, Disiplin ve Günlük İşleyiş Müdürü Başyardımcısı",
            "personality":"Disiplinli, tok sesli, sakin ve belgeye dayalı karar veren.",
            "summary":"Okulun günlük düzeni ve disiplininden sorumlu yönetici; öğrencileri sözle değil kayıtlarla yüzleştirir.",
            "profile_only":True, "country":"turkish"
        },
        {
            "key":"turgut-aksoy", "path":"Alternatif Tarih/Karakterler/Okul/Turgut Aksoy.md", "name":"Turgut Aksoy", "date":"1985 · Mektep yönetimi",
            "role":"Organizasyon, Temsil ve Dış İlişkiler Müdürü",
            "personality":"Nazik, sakin, diplomatik ve temkinli.",
            "summary":"Okulun dış ilişkilerini, yarışma organizasyonunu ve kurumlarla temasını yürüten yönetici.",
            "profile_only":True, "country":"turkish"
        },
        {
            "key":"jale-deniz", "path":"Alternatif Tarih/Karakterler/Okul/Jale Deniz.md", "name":"Jale Deniz", "date":"1985 · Öğretmen kadrosu",
            "role":"Sanat ve Kültür Öğretmeni",
            "personality":"Sessiz, dikkatli, öğrencinin çizdikleri kadar onları neden çizdiğine de önem veren.",
            "summary":"Sanat atölyesinin sakin otoritesi; öğrencilerin ifade edemediklerini çalışmalarından okuyabilen öğretmen.",
            "profile_only":True, "country":"turkish"
        },
        {
            "key":"huseyin-kutlu", "path":"Alternatif Tarih/Karakterler/Okul/Hüseyin Kutlu.md", "name":"Hüseyin Kutlu", "date":"1985 · Öğretmen kadrosu",
            "role":"Tarih Öğretmeni",
            "personality":"Ağırbaşlı, yavaş konuşan, tarihsel ayrıntıları dikkatle tartan.",
            "summary":"Tarihi yalnızca olay sırası olarak değil, alınan kararların ve ödenen bedellerin kaydı olarak anlatan öğretmen.",
            "profile_only":True, "country":"turkish"
        }
    ]
    reich_specs = [
        {
            "key":"reinhard-falkenhorst", "path":"Alternatif Tarih/Karakterler/Reich/Reinhard Falkenhorst.md", "name":"Reinhard Falkenhorst", "date":"1922 doğumlu · 63 yaş",
            "birth":"1922", "age":"63", "role":"Führer und Reichskanzler des Großdeutschen Reiches",
            "personality":"Ağır, soğuk, sabırlı ve hesapçı.",
            "summary":"Reich'ın tepesindeki Führer; parti, SS, ordu ve sanayi arasındaki dengeyi kendi otoritesi altında tutar.",
            "profile_only":True, "country":"german"
        },
        {
            "key":"martin-kessler", "path":"Alternatif Tarih/Karakterler/Reich/Martin Kessler.md", "name":"Martin Kessler", "date":"1930 doğumlu · 55 yaş",
            "birth":"1930", "age":"55", "role":"Führer Yardımcısı · Parti Kanzelleyi Başkanı",
            "personality":"Nazik görünen, sabırlı ve siyasî bağlantıları güçlü.",
            "summary":"Reich içindeki atamaları ve parti disiplinini yöneten etkili iktidar aracısı.",
            "profile_only":True, "country":"german"
        },
        {
            "key":"ulrich-von-havel", "path":"Alternatif Tarih/Karakterler/Reich/Ulrich von Havel.md", "name":"Ulrich von Havel", "date":"1932 doğumlu · 53 yaş",
            "birth":"1932", "age":"53", "role":"Reich Dışişleri Bakanı",
            "personality":"Kibar, sabırlı, hesapçı ve diplomatik baskı kurabilen.",
            "summary":"Türkiye ile ilişkilerde Reich'ın çıkarlarını nezaket ve koşullu teklifler üzerinden gözeten bakan.",
            "profile_only":True, "country":"german"
        },
        {
            "key":"friedrich-wulfhart", "path":"Alternatif Tarih/Karakterler/Reich/Friedrich Wulfhart.md", "name":"Friedrich Wulfhart", "date":"1925 doğumlu · 60 yaş",
            "birth":"1925", "age":"60", "role":"Reichsführer-SS und Chef der Reichssicherheit",
            "personality":"Sessiz, düzen takıntılı, ideolojik açıdan katı ve hesaplı.",
            "summary":"Nazi rejiminin güvenlik ve baskı aygıtını yöneten SS lideri.",
            "profile_only":True, "country":"german"
        },
        {
            "key":"konrad-weissmann", "path":"Alternatif Tarih/Karakterler/Reich/Konrad Weissmann.md", "name":"Konrad Weissmann", "date":"1933 doğumlu · 52 yaş",
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

    teacher_nodes = {}
    for spec in teacher_specs:
        rec = make_public_character("characters", spec)
        if rec:
            teacher_nodes[spec["key"]] = rec

    personal_profiles = {
        "oguz-kagan-atalay": """## Temel bilgiler
**Doğum:** 3 Ocak 1968, İstanbul / Üsküdar  
**Yaş:** 17 (1985)  
**Boy:** 180 cm  
**Fiziksel yapı:** Yapılı, hafif kaslı ve atletik  
**Kanat:** 3  
**Hedef meslek:** Askerî pilot  
**En sevdiği renk:** Kızıl

## Görünüş
Oğuz dik duruşlu, bakımlı ve düzenli görünümüne önem veren bir gençtir. Kaynak karakter dosyasında saç ve göz rengi ile ayrıntılı günlük kıyafet tercihleri kesin olarak belirtilmediğinden bu alanlara ek özellik yüklenmez.

## Kişilik
Sakin, soğukkanlı, disiplinli ve kararlıdır. Gereksiz yere öne çıkmayı sevmez; önce gözlem yapar, sonra hareket eder. Bağımsız çalışmaktan hoşlanır ve başladığı işi tamamlamaya önem verir. Övünmeyi ve yeteneklerini gösteriş için kullanmayı tercih etmez.

Mükemmeliyetçiliği zaman zaman kusursuz sonuç aramasına neden olur. Başarısız olmaktan çekinir ve duygularını açıkça ifade etmek yerine geri planda tutabilir. Aynı anda çok fazla konuyla ilgilendiğinde dikkati dağılabilir.

## İlgi alanları
Askerî havacılık, savaş uçakları, uçak teknolojisi, mekanik sistemler, teknik üretim, tasarım ve geliştirme başlıca ilgi alanlarıdır. Özellikle uçan kanat biçimindeki uçaklara merak duyar. Teknik sistemleri anlamak, parçaları incelemek ve çalışma mantıklarını öğrenmekten hoşlanır.

## Eğitim ve hedef
Havacılık konusunda yaşıtlarının üzerinde teorik bilgiye sahiptir; ancak hikâyenin başlangıcında gerçek pilotluk deneyimi yoktur. En büyük hedefi askerî pilot olmaktır. Disiplinli çalışma, teknik merak ve soğukkanlılık bu hedefe yaklaşırken öne çıkan kişisel özellikleridir.

## Kişisel tercih
En sevdiği renk için özellikle **kızıl** kelimesini kullanır. Birisi buna kırmızı dediğinde kelimeyi düzeltmesi, kendine özgü küçük alışkanlıklarından biridir.""",

        "alev-acar": """## Temel bilgiler
**Doğum yılı:** 1968  
**Yaş:** 17 (1985)  
**Boy:** 168 cm  
**Saç:** Düz, kızıl  
**Göz:** Ela  
**Kanat:** 2  
**Hedef meslek:** Sivil pilot  
**En sevdiği renk:** Kırmızı

## Görünüş ve giyim
Alev'in görünümünde rahatlık ve sportif ayrıntılar öne çıkar. Okulda bol kesimli, pileli siyah kumaş pantolon ve pantolonun içine düzgünce soktuğu siyah forma giyer. Siyah-kırmızı ayrıntılı kemerini ve kemerinin yanındaki zinciri kullanır. Spor ayakkabı tercih eder. Giyiminde gösterişten çok rahat hareket edebilmek ve kendine ait küçük ayrıntılar kullanmak önemlidir.

## Kişilik
Neşeli, hareketli ve konuşkandır. Yeni ortamlara çabuk uyum sağlar; planlar değiştiğinde uzun süre aynı noktada kalmak yerine yeni bir çözüm arar. Gerektiğinde ciddileşebilir ve önemli bir meseleyle karşılaştığında şakayı bırakıp dikkatini konuya verebilir.

İnsanlarla ilk iletişimi kolay kurar, ancak gerçek güvenini kazanmak zaman ister. Sadakat onun için önemli bir değerdir. Kendini hızlı uyum sağlama özelliğiyle beğenir; fazla bağlanmasını ve hayalperestliğini ise zayıf tarafları arasında görür.

## Eğitim ve ilgi alanları
Dersleri genel olarak ortalamanın üzerindedir. En sevdiği ders matematiktir; problem çözmekten ve farklı çözüm yolları denemekten hoşlanır. Türk Dili ve Edebiyatı'nı ise uzun metinler ve ezber ağırlığı nedeniyle daha az sever.

Boş zamanlarında örgü örer ve küçük karakter çizimleri yapar. Çizimleri çoğunlukla defter kenarlarına veya eline geçen kâğıtlara yaptığı kısa karalamalardır.

## Duygusal tepkileri
Eleştiriye ilk anda savunmacı yaklaşabilir; biraz zaman geçince haklı eleştiriyi kabul edebilir. Öfkelendiğinde bağırmaktan çok sert konuşur. Üzgün olduğunda çoğunlukla yalnız kalıp uyumayı tercih eder. En büyük korkusu değer verdiği insanları kaybetmektir.

## Meslek hedefi
Çocukluğundan beri uçakları izlemeye ve uçuşları merak etmeye ilgi duyar. Sivil pilotluk, gökyüzüne duyduğu ilgiyi mesleğe dönüştürme isteğidir.""",

        "aylin-aksoy": """## Temel bilgiler
**Doğum yılı:** 1968  
**Yaş:** 17 (1985)  
**Boy:** 167 cm  
**Saç:** Uzun, kıvırcık, kumral  
**Göz:** Koyu renkli  
**Kanat:** 3  
**Hedef meslek:** Avukat  
**En sevdiği renk:** Mor

## Görünüş ve giyim
Aylin sade ve sportif giyinir. Okul kıyafetinde bol kesimli, uzun ve dökümlü siyah kumaş pantolon, siyah okul forması, beyaz kemer ve spor ayakkabı tercih eder. Gösterişli parçalardan hoşlanmaz; siyah kıyafetle beyaz kemerin oluşturduğu sade zıtlık, tarzının belirgin ayrıntısıdır.

## Kişilik
Sakin, kontrollü ve gözlemcidir. Bir ortama girdiğinde önce çevresini anlamaya çalışır. İnsanlar hakkında acele hüküm vermez; ayrıntıları fark eder ve bir konuyu farklı ihtimaller üzerinden değerlendirmeyi sever.

Planlı olması kendisinde en sevdiği özelliklerden biridir. Buna karşılık fazla düşünmek bazen karar vermesini zorlaştırır. Yanlış anlaşılmaktan ve kontrolü kaybetmekten hoşlanmaz. Eleştiriye açıktır; haklı bir eleştiriyi değerlendirip kabul edebilir. Öfkelendiğinde çoğunlukla sesini yükseltmek yerine sessizleşir.

## Eğitim ve ilgi alanları
Dersleri iyidir. Özellikle müzakere ve savunma uygulamalarının bulunduğu Sosyolojik Eğitim dersini sever. Matematik ise en sevmediği derstir. Bir konuyu tartışmak, farklı görüşlere cevap hazırlamak ve düşüncelerini gerekçelendirmek ilgisini çeker.

Boş zamanlarında müzik dinler, yürüyüş yapar ve bazen kâğıda gelişigüzel çizimler karalar. Düşünürken saçlarıyla oynaması sık görülen küçük bir alışkanlığıdır.

## Hedef
Başarılı bir avukat olmak ister. Mesleğinde yalnızca başarı değil, dürüstlük, güvenilirlik ve işini iyi bilmek sayesinde saygı kazanmayı önemser.""",

        "asena-korkut": """## Temel bilgiler
**Doğum yılı:** 1968  
**Yaş:** 17 (1985)  
**Boy:** 163 cm  
**Saç:** Siyah, hafif kızıla çalan, orta-uzun  
**Göz:** Kahverengi  
**Gözlük:** Kullanır  
**Kanat:** 5  
**Okul:** İstanbul Şarkın İlim ve Teknoloji Lisesi  
**En sevdiği renk:** Turkuaz  
**Hedef meslek:** İstihbarat uzmanı / saha istihbarat subayı

## Görünüş
Asena gözlük kullanır. Siyah saçlarında hafif kızıl ton bulunur; saçları orta-uzun uzunluktadır. Kahverengi gözlüdür. Kaynak notlarında günlük ve okul kıyafetlerinin ayrıntılı tarifi bulunmadığından belirli bir giyim tarzı eklenmemiştir.

## Kişilik
Neşeli, konuşkan ve hareketlidir. İnsanları dinlemeyi ve karşısındaki kişinin ne düşündüğünü anlamaya çalışmayı sever. Sosyal ortamlarda rahattır; buna rağmen herkese aynı yakınlığı göstermez ve özellikle erkeklere karşı daha mesafeli davranır.

Dışarıdan rahat ve kendinden emin görünse de kendisini sık sık sorgular. Bir görevde başarısız olmaktan ve yetersiz görülmekten çekinir. Hata yaptığını kabul edebilir; eleştiriye tamamen kapanmaz. Öfkelendiğinde veya kırıldığında içine kapanabilir, ağlayabilir ya da konuşmayı bırakabilir.

## Yetenekleri ve hedefi
İnsanları dinleme, doğal konuşma kurma ve dikkat çekmeden bilgi edinme konularında başarılıdır. İleride Millî İstihbarat ve Askerî Güvenlik Teşkilatı'nda istihbarat uzmanı veya saha istihbarat subayı olmak ister. Bu hedef, gözlem ve iletişim becerilerini kullanabileceği bir meslek arzusunu yansıtır.

## Kişisel eğilimleri
Kendi ayakları üzerinde durmak ister; ancak özgüveninin zaman zaman zayıflaması kararlarını yeniden sorgulamasına neden olabilir. Kendini geliştirmek ve yeterliliğini kanıtlamak onun için önemlidir.""",

        "tomris-ilter": """## Temel bilgiler
**Doğum yılı:** 1968  
**Yaş:** 17 (1985)  
**Boy:** 170 cm  
**Saç:** Uzun, siyah, düz-dalgalı  
**Göz:** Koyu renkli  
**Kanat:** 6  
**Okul:** İstanbul Şarkın İlim ve Teknoloji Lisesi  
**En sevdiği renk:** Siyah  
**Hedef meslek:** Millî İstihbarat ve Askerî Güvenlik Başkanı

## Görünüş
Tomris uzun, siyah ve düz ile dalgalı arasında görünen saçlara, koyu renk gözlere sahiptir. Kaynak profilde okul dışındaki günlük kıyafetleri hakkında kesin bir tarif bulunmadığı için ayrıca bir giyim tarzı varsayılmaz.

## Kişilik
Ciddi olmasına rağmen konuşkandır; düşüncelerini doğrudan ifade eder ve bulunduğu ortamda doğal bir otorite kurabilir. Özgüveni yüksektir. Yönetmeyi, karar almayı ve düzeni kontrol altında tutmayı sever. Belirsizlikten hoşlanmaz; emir, hiyerarşi ve düzen kavramlarına önem verir.

Stratejik düşünür, bilgileri hızlı sınıflandırır ve ayrıntıları uzun süre hatırlar. İnsanların sözleriyle davranışları arasındaki çelişkileri fark edebilir. Kontrolü kaybetmek en büyük korkularından biridir. Kontrolün elinden çıktığını hissettiğinde sertleşebilir ve öfkesini yönetmekte zorlanabilir.

## Değerleri ve davranış biçimi
Düzenin korunmasını kişisel tercihlerden üstün tutmaya eğilimlidir. Bununla birlikte hedefi için kuralları esnetebilir, gerçeği saklayabilir veya manipülatif davranabilir. Kendi yöntemlerini çoğu zaman ulaşmak istediği sonuç üzerinden gerekçelendirir.

## Hedef
Millî İstihbarat ve Askerî Güvenlik Başkanlığına yükselmek ister. Yalnızca verilen emirleri uygulamak değil, devlet mekanizmasının kararlarını belirleyen makamda bulunmak onun temel meslek hedefidir.""",

        "ismail-yagiz-aslan": """## Temel bilgiler
**Doğum yılı:** 1968  
**Yaş:** 17 (1985)  
**Doğum yeri:** İstanbul / Üsküdar  
**Boy:** 178 cm  
**Fiziksel yapı:** İri yapılı, hafif kilolu  
**Saç:** Siyah  
**Göz:** Kahverengi  
**Kanat:** 5  
**Hedef:** Siyasete atılmak

## Görünüş ve giyim
İsmail siyah saçlı ve kahverengi gözlüdür. İri yapılı bir fiziği vardır. Gündelik ve rahat kıyafetleri tercih eder; eşofman, şort ve tişört sık kullandığı parçalardır. Ayakkabı olarak terlik veya spor ayakkabı giyer.

## Kişilik
Sakin ve neşelidir. Mizahı güçlüdür; çoğu zaman eğlenceli, şakacı ve biraz da laubali davranabilir. Gereksiz gördüğü işlerde üşengeçlik eder, dağınık ve zaman zaman disiplinsiz olabilir. Ancak gerçekten önemsediği bir konuya odaklandığında kararlı biçimde çalışır ve başladığı işi bitirmeye uğraşır.

Bazen düşünmeden hareket ediyormuş gibi görünür; buna rağmen ihtiyaç duyulduğunda pratik ve beklenmedik çözümler üretebilir. Büyüklerine karşı saygılı, günlük konuşmalarında ise rahat ve samimidir.

## Eğitim ve ilgi alanları
Akademik başarısı genel olarak yüksek değildir. Kimya ve matematik, diğer derslere göre daha fazla ilgisini çeken alanlardır. Boş zamanının önemli bölümünü sosyal ortamlarda ve arkadaşlarıyla vakit geçirerek değerlendirir.

## Hedef
İleride siyasete atılmak ister. Siyasi meseleler ve ülkenin geleceği hakkında söz sahibi olma isteği, kişisel hedefleri arasında yer alır.""",

        "muhammed-mete": """## Temel bilgiler
**Doğum yılı:** 1968  
**Yaş:** 17 (1985)  
**Boy:** 182 cm  
**Saç:** Siyah, hafif kıvırcık  
**Göz:** Kahverengi  
**Kanat:** 4  
**Hedef meslek:** Sivil pilot  
**En sevdiği renkler:** Kırmızı ve siyah

## Görünüş
Muhammed Mete uzun boylu, siyah ve hafif kıvırcık saçlı, kahverengi gözlüdür. İlk bakışta sakin ve ağırbaşlı görünür; fazla dikkat çekmeye çalışmaz.

## Kişilik
Ölçülü ve soğukkanlıdır. Kendini rahat hissettiği ortamlarda neşeli, enerjik ve konuşkan bir hâle gelir. Yeni ortamlara ve değişen şartlara hızlı uyum sağlayabilir. İnsanlara genellikle güvenle yaklaşır; ancak kendi yetenekleri söz konusu olduğunda zaman zaman özgüvenini sorgular.

Bir hedef belirlediğinde kolay vazgeçmez ve istediği sonucu elde edemediğinde başka bir yol denemeye çalışır. Eleştirilerden etkilenir; haklı bulduğu eleştiriyi kabul eder, haksız bulduğunda ise düşüncesini gerekçelendirmek ister. Öfkelendiğinde çoğunlukla sessizleşir ve soğuklaşır.

## Eğitim ve ilgi alanları
Dersleri iyidir. En sevdiği ders biyoloji, en az sevdiği ders edebiyattır. Boş zamanlarında resim çizer, kitap okur ve müzik dinler. Düşünürken elini çenesiyle burnu arasındaki bölgeye götürmesi sık tekrarladığı küçük bir alışkanlıktır.

## Hedef
Sivil pilot olmak ister. Pilotluğu farklı yerleri görmek, yeni bölgeler keşfetmek ve özgür hissetmekle ilişkilendirir. Başarı onun için kişisel olduğu kadar kendini geliştirme ve hedeflerine ulaşma anlamı da taşır.""",

        "cengiz-atalay": """## Temel bilgiler
**Doğum yılı:** 1945  
**Yaş:** 40 (1985)  
**Boy:** 182 cm  
**Fiziksel yapı:** Yapılı ve atletik  
**Meslek:** Askerî uçak mühendisi  
**En sevdiği renk:** Su yeşili

## Görünüş ve giyim
Cengiz yapılı ve atletik bir görünüme sahiptir. Saçları hafif seyrektir ve genellikle arkaya doğru tarar. Resmî, klasik ve hafif askerî çizgileri sever. Takım elbise ile beyaz veya gri mühendis önlüğü en sık kullandığı kıyafetler arasındadır.

## Kişilik
Özgüvenli, enerjik, meraklı ve çalışmayı seven biridir. Yaptığı işe yüksek ilgi duyar; çalışmalarının fark edilmesinden ve gerektiğinde ön plana çıkmaktan hoşlanır. El becerisi, analitik düşünme ve problem çözme konusunda güçlüdür. Var olan sistemlerdeki eksikleri fark edip onları geliştirmekten keyif alır.

İşine fazla yoğunlaştığında diğer sorumluluklarını aksatabilir. Duygusal yönü belirgindir ve zor durumda kısa süreli telaşa kapılabilir.

## Mesleki ilgi alanları
Askerî havacılık, uçak mühendisliği, teknik tasarım ve mevcut sistemleri geliştirmek temel uğraş alanlarıdır. Bir sorunu yalnızca tespit etmekle kalmayıp daha iyi çalışan bir çözüm üretmeye odaklanır.

## Dünya görüşü
Birlikçi fakat özgürlükçü bir anlayışa sahiptir. Devlet ve toplum birliğini önemserken bireysel özgürlüklerin de korunması gerektiğine inanır.""",

        "aysel-atalay": """## Temel bilgiler
**Doğum yılı:** 1947  
**Yaş:** 38 (1985)  
**Meslek:** Ev hanımı

## Görünüş ve giyim
Aysel sade ve zarif bir görünümü tercih eder. Genellikle elbise, etek-bluz, sade gömlek, örgü ve kazak gibi klasik ve dönemine uygun kıyafetler giyer. Giyiminde gösterişten çok düzen ve zarafete önem verir.

## Kişilik
Sakin, sabırlı, anlayışlı ve şefkatlidir. Ev hayatında huzuru önemser; insanları dikkatle gözlemler ve zor zamanlarda soğukkanlı kalabilir. Bazen fazla endişelenebilir ve kendi ihtiyaçlarını başkalarının ihtiyaçlarının gerisine atabilir.

## Değerleri
Güven, huzur, anlayış ve insanların güven içinde yaşayabilmesi onun için önemlidir. Askerî veya siyasî meselelerden çok günlük hayatın düzenine ve insanların iyiliğine odaklanır.""",

        "nec-det-atalay": """## Temel bilgiler
**Doğum yılı:** 1918  
**Yaş:** 67 (1985)  
**Meslek:** Askerî uçak mühendisi  
**Mesleki çalışması:** TA-85 Gökkanat projesinde görev aldı

## Kişilik
Ağırbaşlı, disiplinli, otoriter ve az konuşan bir adamdır. Düzeni, sorumluluğu ve çalışmayı ön planda tutar. Zor durumda kolay paniğe kapılmaz; sakinliğini korur ve kararlarını kararlılıkla uygular. Geleneklerine bağlıdır. Duygularını sözle ifade etmekte zorlanabilir.

## Görünüş ve giyim
Gençliğinde gömlek, kumaş pantolon ve kundura gibi sade ve resmî kıyafetler tercih eder. Yaşlandıkça daha rahat parçalara yönelir; kazakları daha sık kullanır. Genel görünümünde temizlik ve düzen önemlidir.

## Dünya görüşü
Güçlü, otoriter ve merkezî bir devlet yapısının gerekli olduğuna inanır. Devlet otoritesinin zayıflamasının toplumsal düzeni bozacağını düşünür. Birlik ve beraberliği temel değerler arasında görür.""",

        "sabiha-atalay": """## Temel bilgiler
**Doğum yılı:** 1923  
**Yaş:** 62 (1985)  
**Meslek:** Ev hanımı

## Kişilik
Sakin, sabırlı, şefkatli ve anlayışlıdır. İnsanları iyi gözlemler, kriz anlarında soğukkanlı kalabilir ve fedakâr davranır. Geleneklerine bağlıdır. Kendi ihtiyaçlarını geri plana atması ve sevdikleri için fazla endişelenmesi zayıf yönleridir.

## Görünüş ve giyim
Gençliğinde sade ve dönemine uygun giyinir. Yaşlandıkça rahat ve klasik kıyafetleri tercih eder. Elbise, etek-bluz, hırka, kazak ve sade ev kıyafetleri gardırobunun temel parçalarıdır. Temiz ve bakımlı görünmeye önem verir.

## Değerleri
Aile huzuru, sadakat, güven, sevgi ve gelenekler onun için önemlidir. Günlük hayatında gösterişten çok düzen ve sakinliği tercih eder.""",

        "naciye-kaya": """## Temel bilgiler
**Doğum yılı:** 1920  
**Yaş:** 65 (1985)  
**Meslek:** Ev hanımı

## Kişilik
Konuşkan, girişken, hareketli ve açık sözlüdür. Düşündüğünü söylemekten çekinmez; gerektiğinde sert biçimde karşı çıkabilir. Pratik zekâlıdır ve günlük sorunlara hızlı çözümler bulur. Kolay pes etmez ve zor kararlar almaktan kaçınmaz.

Bazen düşünmeden konuşabilir, fazla müdahaleci veya inatçı davranabilir. Korumacı tavrı zaman zaman ağır basabilir.

## Görünüş ve giyim
Yaşına uygun, sade ve geleneksel kıyafetler tercih eder. Elbise, etek-bluz, hırka, kazak, sade başörtüsü ve ev kıyafetleri kullanır. Rahatlık ve düzen, görünüşünde gösterişten daha önemlidir.

## Dünya görüşü
Dayanışmaya, sorumluluğa ve geleneklere değer verir. İnsanların kendi kararlarını verebilmesini önemser; ancak korumacı ve müdahaleci tarafı zaman zaman ağır basabilir.""",

        "riza-kaya": """## Temel bilgiler
**Doğum yılı:** 1916  
**Yaş:** 69 (1985)

## Kişilik
Sakin, ağırbaşlı, sabırlı ve geleneklerine bağlıdır. Sorumluluklarını önemser; kolay öfkelenmez ve kararlarını düşünerek vermeyi tercih eder. Güvenilir ve sağduyulu bir karaktere sahiptir. Duygularını açıkça ifade etmekte zorlanabilir ve bazen fazla korumacı davranabilir.

## Görünüş ve giyim
Gençliğinde gömlek, kumaş pantolon ve kundura gibi klasik kıyafetler giyer. Yaşlandıkça koyu renk ceketler, kazaklar ve kumaş pantolonlar gibi daha rahat ve sade parçalara yönelir. Bakımlı ve ağırbaşlı bir görünümü vardır.

## Dünya görüşü
Aile, düzen, gelenek ve toplumun birlik içinde olması önem verdiği değerlerdir. Hayatının merkezine siyasî veya askerî düşünceleri değil, gündelik hayatın huzurunu koyar.""",

        "meliha-atalay": """## Temel bilgiler
**Doğum yılı:** 1975  
**Yaş:** 10 (1985)  
**Boy:** 138 cm  
**Fiziksel yapı:** İnce yapılı  
**Hedef meslek:** Avukat  
**En sevdiği renk:** Mor

## Görünüş ve giyim
Meliha ince yapılıdır. Özel veya gösterişli bir giyim tarzı yoktur; yaşına uygun, rahat ve gündelik kıyafetler giyer. Tişört, gömlek, etek, pantolon, kazak, mont ve spor ayakkabı tercih eder.

## Kişilik
Çalışkan, kararlı, inatçı ve disiplinlidir. Bir şeyi kafasına koyduğunda uzun süre uğraşır ve kolay vazgeçmez. Özgüvenli, zeki ve adalet duygusu güçlüdür; düşündüğünü açıkça söyler ve tartışmaktan çekinmez.

Aşırı inatçılık, sabırsızlık ve zaman zaman gereğinden sert konuşmak zayıf yanlarıdır. Haklı olduğuna inandığında fikrini değiştirmesi kolay değildir.

## Hedef ve değerler
Avukat olmak ister. Hukuka, adalete ve insanların haklarını savunma düşüncesine ilgi duyar. Haksızlık gördüğünde sessiz kalmamayı ve doğru bildiği düşünceyi savunmayı önemser.""",

        "muhammed-atalay": """## Temel bilgiler
**Doğum yılı:** 1973  
**Yaş:** 12 (1985)  
**Boy:** 150 cm  
**Fiziksel yapı:** Hafif kilolu  
**Hedef meslek:** Askerî mühendis  
**En sevdiği renk:** Turkuaz

## Görünüş ve giyim
Muhammed çocuk yaşta, hafif kilolu bir yapıya sahiptir. Askerî veya klasik giyime özel bir ilgisi yoktur. Tişört, gömlek, pantolon, kazak, mont ve spor ayakkabı gibi sade, yaşına uygun kıyafetler giyer.

## Kişilik
Sakin, uyumlu ve meraklıdır. Teknik konulara ilgisi vardır; ancak uzun süre çalışmayı sevmez ve yapması gereken işleri erteleyebilir. Rahatına düşkün ve zaman zaman üşengeçtir. Kolay öfkelenmez, pratik yollar bulmayı sever.

## İlgi alanları ve hedef
Uçak motorları, mekanik sistemler, uçak yapıları, askerî teknoloji ve yeni tasarımlar ilgisini çeker. Askerî mühendis olmayı ister. Bu istek, teknik sistemlerin nasıl yapıldığını ve geliştirildiğini öğrenme merakından kaynaklanır.""",

        "alper-ulac-altayli": """## Temel bilgiler
**Doğum yılı:** 1968  
**Yaş:** 17 (1985)  
**Kanat:** 6  
**Görev:** Üsküdar Milli İlim ve İrfan Mektebi okul başkanı

## Kişilik
Sakin, kontrollü ve stratejik düşünen bir öğrencidir. Okul yönetiminde bilgi toplama, gelişmeleri takip etme ve kararları planlı biçimde ele alma eğilimindedir. Otoritesini yüksek sesle değil, ölçülü ve kararlı davranarak kurar.

## Bilinen kişisel bilgiler
Mevcut eski karakter dosyalarında Alper'in boyu, saç ve göz rengi, sevdiği renk, hobileri ve günlük kıyafetleri hakkında doğrulanmış ayrıntı bulunmamaktadır. Bu nedenle bu alanlara tahminî özellik eklenmemiştir.""",

        "abdullah-keser": """## Temel bilgiler
**Doğum:** 1770 civarı, Giresun / Kuşköy  
**Ölüm:** 1830'lar civarı  
**Meslek:** Demirci ve köy zanaatkârı  
**Köken ve inanç:** Türk, Müslüman

## Kişilik
Sert mizaçlı ve az konuşan biridir. Kendini sözle değil, yaptığı işle ve emeğiyle anlatır. Duygularını açıkça göstermese de sorumluluk duygusu güçlüdür. İnsanların değerini sözlerinden çok emekleri ve davranışları üzerinden değerlendirir.""",

        "oguz-keser": """## Temel bilgiler
**Doğum:** 1802, Giresun / Kuşköy  
**Ölüm:** 1898  
**Yaş:** 96  
**Meslek:** Demirci  
**Lakap:** Keser  
**İnanç:** Müslüman

## Kişilik
Sarsılmaz psikolojili, dürüst, sevecen ve cana yakın bir insandır. Yanlış gördüğü bir şeyi, karşısındaki kim olursa olsun açıkça söylemekten çekinmez. Güçlü iradeye sahiptir; ancak sevdiklerine aşırı bağlılığı bazen kendi ihtiyaçlarını ikinci plana atmasına neden olabilir.

## İlgi alanları ve dünya görüşü
Boş zamanlarında demircilikle uğraşır ve metal oyuncaklar yapar. Devletin güçlü ve merkezî olmasını, toplumun birlik içinde kalmasını önemser. Savaşların yol açtığı can kayıplarından üzüntü duyar ve savaşı son çare olarak görür. Dini değerlerine bağlıdır.""",

        "gul-keser": """## Temel bilgiler
**Doğum:** 1810 civarı, Giresun çevresi

## Kişilik
Sabırlı, sezgileri güçlü ve insanları iyi okuyabilen biridir. Çevresindeki gerilimleri erken fark eder ve sakinleştirici bir yaklaşım sergiler. Kaynak dosyada dış görünüş, giyim, hobiler veya sevdiği renk gibi kişisel tercihler ayrıntılandırılmamıştır.""",

        "kaan-keser": """## Temel bilgiler
**Doğum:** 1846, Giresun / Kuşköy  
**Ölüm:** 1904  
**Yaş:** 58  
**Meslek:** Demirci  
**Lakap:** Keser  
**İnanç:** Müslüman

## Kişilik
Sakin, tutkulu, azimli, güçlü ve erdemli bir karakterdir. Çalışkanlığı, başladığı işi sonuna kadar götürmesi ve sorumluluk duygusu güçlü yönleridir. Duygularının ve sorumluluklarının zaman zaman kararlarını etkilemesi zayıf yönü olabilir.

## İlgi alanları ve değerleri
Avlanmak ve demir aletler yapmak alışkanlıkları arasındadır. Din, kültür, aile ve millet temel değerleridir. Milliyetçiliği birlik fikrine dayanır; toplumdaki ayrılıkların devleti zayıflatacağına inanır. Savaşların getirdiği ölüm ve yıkımdan rahatsızlık duyar.""",

        "ali-keser": """## Kişilik ve yaşam
Tarım işleriyle uğraşır, dönem dönem demircilik işlerine yardım eder. Hareketli, meraklı ve bağımsız bir karakterdir. Çabuk öfkelenebilir; ancak öfkesi uzun sürmez ve kısa sürede yumuşar. Sürekli aynı düzen içinde kalmaktan hoşlanmaz.""",

        "firuze-keser": """## Kişilik
Sabırlı, içine kapanık ve duygularını çoğunlukla davranışlarıyla gösteren biridir. Duygularını konuşarak dışa vurmak yerine içinde tutma eğilimi vardır. Gerektiğinde dirençli ve kararlı davranabilir. Kaynak notlarda görünüşü, giyim tarzı ve kişisel zevkleri ayrıntılı olarak belirtilmemiştir.""",

        "alperen-keser": """## Temel bilgiler
**Doğum:** 1888, Giresun / Kuşköy  
**Resmî doğum tarihi:** 1 Ocak 1888  
**Meslek:** Demirci, asker ve devlet adamı  
**Siyasi düşünce:** Türk milliyetçiliği ve güçlü merkezî devlet anlayışı  
**İnanç:** Müslüman

Köyde doğum kayıtları düzenli tutulmadığı için gerçek doğum günü ve ayı bilinmez. Harman biçildiği dönemde doğduğu aktarılır; daha sonraki resmî kayıtlarda 1 Ocak 1888 tarihi kullanılmıştır.

## Kişilik ve dünya görüşü
Disiplinli, sorumluluk sahibi, çalışkan ve kararlıdır. Çocukluk ve gençlik deneyimleri milliyetçi ve devletçi düşüncelerini şekillendirmiştir. Güçlü merkezî yönetim, teşkilatlı ordu ve sanayileşme onun devlet anlayışının temel unsurlarıdır.

## Mesleki yaşam
Demircilikten askerî hayata ve devlet yönetimine uzanan bir yaşam sürmüştür. 29 Kasım 1938'de yönetimi devralmıştır. Görünüşü, giyim tercihleri ve sevdiği renk gibi kişisel ayrıntılar eski karakter dosyasında kesin biçimde belirtilmemiştir.""",

        "ismail-karaslan": """## Temel bilgiler
**Doğum:** 1904, Hatay  
**Meslek:** Asker ve devlet adamı  
**Askerî köken:** Piyade  
**İktidar dönemi:** 1960–1975  
**1960'taki yaşı:** 56  
**1975'teki yaşı:** 71

## Kişilik
Alperen Keser'den daha sakin, hesapçı ve sabırlı bir karakterdir. Toplantılarda önce dinlemeyi, farklı görüşleri toplamayı ve kararını verdikten sonra kararlılıkla uygulamayı tercih eder. Disiplinli, temkinli ve uzun vadeli düşünen bir yöneticidir.

## Askerî ve idarî yaklaşım
Askerî strateji, kriz yönetimi, teşkilatçılık ve uzun vadeli planlama güçlü yönleridir. Kurumların devamlılığına büyük önem verir. Devlet kurumlarına aşırı güvenmek ve mevcut düzeni fazla muhafazakâr biçimde korumak zayıf yönleri arasında sayılır.""",

        "selim-arkan": """## Temel bilgiler
**Doğum:** 1935, Ankara  
**Yaş:** 50 (1985)  
**Meslek:** Siyasetçi ve devlet adamı  
**Askerî geçmiş:** Yok  
**İktidara gelişi:** 1975  
**Siyasi çizgi:** Milliyetçi, devletçi, merkeziyetçi; zamanla bağımsızlıkçı ve Nazi karşıtı

## Kişilik
Önceki liderlerden daha sosyal, konuşkan ve siyaseten hesapçı bir karakterdir. İnsanları ikna etmeyi sever; doğrudan emir vermek yerine karşısındakini kendi düşüncesinin doğruluğuna inandırmayı tercih eder.

## Güçlü ve zayıf yönleri
Siyasi zekâ, diplomasi, tarih ve ekonomi bilgisi, kriz yönetimi ve farklı çevrelerle iletişim kurabilme güçlü yanlarıdır. Fazla pragmatik davranması, siyasi hesapları kişisel yakınlıkların önüne koyması ve merkezî güce gereğinden fazla önem vermesi zayıf yanlarıdır.""",

        "kaan-demirsoy": """## Kişisel profil
1936 doğumlu Kaan Demirsoy, Başbuyruk makamını yürütür. Sessiz, titiz ve sabırlıdır. Resmî kararların doğru metinle kayda geçirilmesine, belgelerin geçerliliğine ve idarî düzenin tutarlılığına önem verir. Konuşurken ölçülü ve maddeler hâlinde ilerler. Eski karakter kaynaklarında fiziksel görünüşü ve kişisel hobileri belirtilmemiştir.""",

        "sabiha-erten": """## Kişisel profil
1945 doğumlu Sabiha Erten, Başbuyruk Kalemi Müsteşarıdır. Dikkatli, titiz ve sessiz çalışır. Kararname nüshaları, mühür düzeni ve toplantı tutanaklarındaki ayrıntıları takip eder. Bir belgedeki küçük tutarsızlığın idarî sonuçlarını önemser. Kaynaklarda fiziksel görünüşü veya kişisel hobileri hakkında bilgi verilmemiştir.""",

        "mete-kutlu": """## Kişisel profil
1931 doğumlu Mete Kutlu, İmparatorluk İstihbarat Başkanıdır. Sakin, sabırlı ve ölçülü bir dinleyicidir. Dış ve stratejik istihbarat konularında uzun vadeli değerlendirmeyi önemser. Bilgiyi toplamak kadar doğru zamanda ve doğru makamla paylaşılmasını da görev anlayışının parçası sayar. Fiziksel görünüşü ve kişisel hobileri kaynakta belirtilmemiştir.""",

        "rana-tozun": """## Kişisel profil
1938 doğumlu Rana Tözün, Bilim ve Gök Araştırmaları Başkanıdır. Sakin, kesin ve veriye bağlı bir çalışma tarzına sahiptir. Bilimsel sonuçların kişisel kanaatlerden önce gözlem ve ölçümle desteklenmesini ister. Genç araştırmacılara karşı koruyucu, bilimsel çalışmaları aksatan bürokratik engellere karşı kararlıdır. Dış görünüşü ve hobileri kaynakta belirtilmemiştir.""",

        "ziya-arat": """## Kişisel profil
1934 doğumlu Ziya Arat, Maarif ve Gençlik Nazırıdır. Enerjik ve ikna edici bir konuşma tarzı vardır. Eğitim, müfredat, mektepler ve gençlik politikası alanlarında çalışır. Okulların işleyişini ve gençlerin yetişmesini devletin uzun vadeli geleceği açısından değerlendirir. Fiziksel görünüşü ve kişisel zevkleri kaynaklarda belirtilmemiştir.""",

        "haluk-sancar": """## Kişisel profil
1927 doğumlu Haluk Sancar, Afrika Umumi Valisidir. Enerjik, konuşkan ve ikna edici bir yöneticidir. Siyasî dengeyi gözetir; reform hedefleri ile mevcut idarî uygulamalar arasında sonuç almaya çalışır. Fiziksel görünüşü ve hobileri hakkında doğrulanmış bilgi bulunmamaktadır.""",

        "reinhard-falkenhorst": """## Kişisel profil
1922 doğumlu Reinhard Falkenhorst, Großdeutsches Reich'ın Führer und Reichskanzler makamındadır. Ağır, soğuk, sabırlı ve hesapçı bir karaktere sahiptir. Kararlarında dosyalara, raporlara ve kurumsal dengeye önem verir. Fiziksel görünüşü ve kişisel hobileri mevcut kaynaklarda belirtilmemiştir.""",

        "martin-kessler": """## Kişisel profil
1930 doğumlu Martin Kessler, Führer Yardımcısı ve Parti Kanzelleyi Başkanıdır. Nazik görünür, sabırlıdır ve siyasî bağlantıları güçlüdür. Parti disiplini, üst düzey atamalar ve idarî devamlılık konularında etkilidir. Kişisel görünüşü ve hobileri hakkında kaynaklarda ayrıntı bulunmamaktadır.""",

        "ulrich-von-havel": """## Kişisel profil
1932 doğumlu Ulrich von Havel, Reich Dışişleri Bakanıdır. Kibar, sabırlı ve hesapçı bir diplomattır. Görüşmelerde nezaketini korurken tekliflerin şartlarını ve karşı tarafın hareket alanını dikkatle hesaplar. Görünüşü ve özel ilgi alanları kaynakta belirtilmemiştir.""",

        "friedrich-wulfhart": """## Kişisel profil
1925 doğumlu Friedrich Wulfhart, Reichsführer-SS ve Reich güvenlik teşkilatının başındaki isimdir. Sessiz, düzen takıntılı, ideolojik açıdan katı ve hesaplıdır. Otoritesini yüksek sesle değil, sorgulama ve kayıt düzeni üzerinden kurar. Fiziksel görünüşü ve hobileri hakkında kaynaklarda bilgi bulunmamaktadır.""",

        "konrad-weissmann": """## Kişisel profil
1933 doğumlu Konrad Weissmann, baş nükleer fizikçi olarak SFA-P Polaris araştırmalarıyla ilişkilidir. Sabırsız, keskin, kibirli ve veriye odaklıdır. İnsan ilişkilerinden çok ölçümlere ve bilimsel sonuçlara önem verir. Fiziksel görünüşü ve kişisel hobileri kaynakta belirtilmemiştir.""",

        "nihat-karaca": """## Kişisel profil
Nihat Karaca, mektebin Düzen, Disiplin ve Günlük İşleyiş Müdürü Başyardımcısıdır. Disiplinli, tok sesli ve sakindir. Karar verirken söylentilerden çok kayıtları ve somut bilgileri esas alır. Kaynaklarda fiziksel görünüşü ve özel ilgi alanları belirtilmemiştir.""",

        "turgut-aksoy": """## Kişisel profil
Turgut Aksoy, mektebin Organizasyon, Temsil ve Dış İlişkiler Müdürüdür. Nazik, sakin, diplomatik ve temkinlidir. Kurumlar arası görüşmelerde ölçülü bir dil kullanır ve temsil görevini dikkatle yürütür. Fiziksel görünüşü ve hobileri kaynaklarda belirtilmemiştir.""",

        "jale-deniz": """## Kişisel profil
Jale Deniz, Sanat ve Kültür öğretmenidir. Sessiz, dikkatli ve gözlemci bir öğretim tarzına sahiptir. Öğrenci çalışmalarını yalnızca teknik sonuçlarına göre değil, taşıdıkları düşünce ve ifade biçimine göre de değerlendirir. Fiziksel görünüşü ve kişisel hobileri kaynakta belirtilmemiştir.""",

        "huseyin-kutlu": """## Kişisel profil
Hüseyin Kutlu, tarih öğretmenidir. Ağırbaşlı ve dikkatli konuşur. Tarih dersinde olayların sırasını aktarmakla yetinmez; tarihî kararların nedenlerini ve sonuçlarını öğrencilerin düşünmesini ister. Görünüşü ve özel ilgi alanları kaynakta belirtilmemiştir."""
    }

    profile_sources = {}
    profile_sources.update(main_nodes)
    profile_sources.update(political_nodes)
    profile_sources.update(state_nodes)
    profile_sources.update(reich_nodes)
    profile_sources.update(teacher_nodes)

    for key, profile in personal_profiles.items():
        record = profile_sources.get(key)
        if record:
            record["content"] = profile

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

    school_staff = make_character_group(
        "Mektep yönetimi ve öğretmenleri", "OKUL KADROSU",
        "Öğrencilerin disiplin, temsil, sanat ve tarih eğitimiyle doğrudan ilişkili yetişkinler.",
        collect(["nihat-karaca","turgut-aksoy","jale-deniz","huseyin-kutlu"], teacher_nodes),
        "school-staff"
    )

    roots = [young_people, atalay_suyu, keser_soyu, state_leaders, reich_leadership, school_staff]
    roots = [item for item in roots if item.get("children")]
    if not roots:
        return None

    return {
        "id":"characters",
        "title":"Karakterler",
        "description":"Genç kuşak, Atalay ve Keser aileleri, mektep kadrosu, imparatorluk yönetimi ve Reich çevresi. Karakterlerin görevleri, hedefleri, kişilikleri ve birbirleriyle ilişkileri birlikte ele alınır.",
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

    institution_overviews = [
        {
            "title":"Mektepler — 1985 Eğitim Düzeni",
            "path":"Kuruluşlar/Mektepler - 1985 Eğitim Düzeni.md",
            "sourceName":"Mektepler",
            "summary":"Beş yıllık lise düzeyindeki mektepler, genel eğitimi Teknoloji ve Tasarım ağırlığıyla birleştirir; Üsküdar ve Şarkın iki ana öğrenci ekolünü temsil eder.",
            "country":"turkish",
            "content":"""# Mektepler — 1985 Eğitim Düzeni

## Mektep nedir?
Mektepler, imparatorlukta lise düzeyindeki beş yıllık eğitim kurumlarıdır. Genel derslerin yanında Teknoloji ve Tasarım alanına özel ağırlık verilir. Öğrenciler yalnızca sınav başarısıyla değil; grup çalışması, sorumluluk, temsil ve proje üretimi gibi alanlarda da değerlendirilir.

Mektepler Maarif ve Gençlik Nizamı'na bağlıdır. Denetim; müfettişler, okul Kanat Konseyleri ve Hilalifiyet sistemi üzerinden yürür.

## İstanbul'daki iki ana ekol
**Üsküdar Milli İlim ve İrfan Mektebi**, Üsküdar Bloğu'nun merkez okuludur. İrfan ekolünü temsil eder; teknik merak ile edebiyat ve hukuk alanlarını birlikte önemser. Oğuz, Alper, İsmail, Muhammed Mete, Aylin ve Alev'in öğrenim gördüğü B-3 sınıfı bu okuldadır.

**İstanbul Şarkın İlim ve Teknoloji Mektebi**, Şark Bloğu'nun merkez okuludur. Otorite ekolüyle, teknoloji ve istihbarat alanlarına verdiği ağırlıkla tanınır. Tomris ve Asena bu okulda öğrenim görür. Tomris okul başkanı, Asena başkan yardımcısıdır.

Bu iki mektep aynı şehirde bulunur; ancak ayrı öğrenci çevrelerine, yönetim kadrolarına ve blok ilişkilerine sahiptir. Tomris ile Asena'yı Üsküdar'daki B-3 sınıfının öğrencisi olarak tanıtmak yanlıştır.

## Blok okulları
Üsküdar Bloğu'nun çevresinde Kadıköy İleri Sanayi ve Askeri İdadi, Beyoğlu Fen ve Havacılık Akademisi ve Ümraniye Anadolu İrfan Mektebi bulunur.

Şark Bloğu'nun çevresinde Beşiktaş Siyasi ve Teknolojik Bilimler, Fatih Klasik Edebiyat ve Hukuk ve Bakırköy Teknik Araştırma İdadisi yer alır.

Bu okullar arasındaki bağ yalnızca akademik değildir; öğrenci temsilciliği, ittifaklar, müzakere ve yıllık yarışmalar da blok ilişkilerinin parçasıdır.

## Ortak okul hayatı
Sabah törenleri, marşlar, Alp selamı, haftalık sicil, dönem sonu müzakereleri ve yıllık Teknoloji Tasarım Yarışması mektep hayatının ortak unsurlarıdır. Her okul kendi ekolünü ve temsil biçimini korurken imparatorluğun ortak eğitim düzenine bağlıdır.

## 1985'teki önem
Mektepler gençlerin gelecekteki meslek ve görev alanlarına hazırlandığı yerlerdir. B-3'ün hikâyedeki önemi, farklı ilgi alanlarına sahip öğrencileri aynı sınıfta buluşturmasıdır. Üsküdar ve Şarkın arasındaki rekabet ise kişisel arkadaşlıkları, öğrenci siyasetini ve devletin gençlik politikasını birbirine bağlar."""
        },
        {
            "title":"İstihbarat ve İç Emniyet — İki Kurum",
            "path":"Kuruluşlar/İstihbarat ve İç Emniyet.md",
            "sourceName":"İstihbarat ve Emniyet",
            "summary":"Dış tehditleri izleyen İmparatorluk İstihbarat Başkanlığı ile ülke içindeki gözetim ve güvenliği yürüten İç Emniyet Başdirektörlüğü ayrı görev ve kültürlere sahiptir.",
            "country":"turkish",
            "content":"""# İstihbarat ve İç Emniyet — İki Kurum

## İmparatorluk İstihbarat Başkanlığı
Mete Kutlu'nun yönettiği İmparatorluk İstihbarat Başkanlığı, dış ve stratejik istihbarattan sorumludur. Reich masası, yabancı başkentlerdeki kaynaklar, teknik istihbarat ve karşı istihbarat bu kurumun başlıca çalışma alanlarıdır.

Kurumun çalışma kültürü sabır ve uzun vadeli değerlendirmeye dayanır. Bilgiyi toplamak tek başına yeterli sayılmaz; hangi bilginin ne zaman ve kime aktarılacağı da önemlidir.

## İç Emniyet Başdirektörlüğü
Selahattin Akgün'ün yönettiği İç Emniyet Başdirektörlüğü ülke içindeki gözetim, kayıt, kritik tesis güvenliği ve sansür faaliyetlerinden sorumludur. Okullar ve üniversiteler de bu denetim alanının içindedir.

İç Emniyet'in yaklaşımı daha hızlı ve sicil merkezlidir: şüpheli görülen gelişmeler kayda alınır, kişiler ve kurumlar izlenir. Bu görev alanı, istihbarat başkanlığının dış odaklı çalışmasından farklıdır.

## İki kurum arasındaki ilişki
İki teşkilat aynı devlet adına çalışsa da birbirine bütünüyle güvenmez. İstihbarat dışarıdaki tehditlere odaklanırken İç Emniyet ülke içindeki düzeni korumayı önceler. Ulu Han'ın bu rekabeti denetim altında tutması, hiçbir kurumun tek başına bütün güvenlik alanını kontrol etmemesini sağlar.

## Okur için ayrım
Bir yabancı devletin planını, elçilik temasını veya dışarıdaki ajan ağını araştıran yapı İmparatorluk İstihbarat Başkanlığı'dır. Ülke içindeki bir okulun, tesisin veya kişinin sicilini izleyen yapı ise İç Emniyet Başdirektörlüğü'dür. İki kurumun yetkileri birbirine karıştırılmamalıdır."""
        },
        {
            "title":"Großdeutsches Reich Kurumları — Yönetim Yapısı",
            "path":"Kuruluşlar/Reich Kurumları.md",
            "sourceName":"Reich Kurumları",
            "summary":"Reich yönetimi parti, şansölyelik, dışişleri, ordu, SS ve sanayi çevreleri arasında kurulan sert bir güç dengesiyle işler.",
            "country":"german",
            "content":"""# Großdeutsches Reich Kurumları — Yönetim Yapısı

## Parti-devlet
Reich'ın başında Führer und Reichskanzler Reinhard Falkenhorst bulunur. Reich Şansölyeliği kararname ve protokol işlerini yürütür. Martin Kessler'in başındaki NSDAP Parti Kanzelleyi ise üst düzey atamalar, parti disiplini ve siyasî devamlılıkla ilgilenir.

## Diplomasi ve propaganda
Ulrich von Havel'in yönettiği Auswärtiges Amt dış ilişkileri ve diplomatik temasları yürütür. Basın ve radyo üzerindeki ideolojik denetim Propaganda Bakanlığı'nın görev alanıdır. Ekonomi ve ulaştırma kurumları ise sanayi tahsisi, demiryolu ve stratejik bağlantılar üzerinde etkilidir.

## Silahlı kuvvetler ve güvenlik
OKW, Heer, Luftwaffe ve Kriegsmarine Reich'ın askerî yapısını oluşturur. Friedrich Wulfhart'ın yönettiği SS-Reichssicherheitsapparat ise rejimin güvenlik ve baskı aygıtının merkezindedir. Gestapo ve dış istihbarat birimleri bu denetim yapısının farklı parçalarıdır.

## Bilim ve özel teknoloji
Reich Bilim ve Özel Teknoloji Dairesi ile Reich Yüksek Enerji Fiziği Enstitüsü, rejimin ileri araştırma alanlarında görev yapar. Konrad Weissmann yüksek enerji fiziği ve SFA-P Polaris araştırmalarıyla ilişkilidir.

## Güç dengesi
Reich'ta parti, SS, ordu ve sanayi birbirleriyle rekabet eder. Führer bu kurumların tamamını tek çizgide tutmaya çalışır. Bu yapı karar almayı yavaşlatabilir; buna karşılık rejimin cezalandırma ve güvenlik mekanizmaları son derece hızlı çalışır.

Reich'ın kurumsal düzeni, sıradan bir bürokrasi değil, Nazi ideolojisi ve baskı üzerine kurulu bir parti-devlet yapısıdır."""
        }
    ]
    institution_titles = {normalize(record.get("title", "")) for record in records}
    for item in institution_overviews:
        if normalize(item["title"]) in institution_titles:
            continue
        doc = {
            "title":item["title"], "summary":item["summary"], "content":item["content"],
            "path":item["path"], "sourceName":item["sourceName"], "aliases":[],
            "country":item["country"]
        }
        records.append(node("institutions", doc))
        records[-1]["country"] = item["country"]

    for record in records:
        if normalize(record.get("title", "")).startswith("hilalifiyet merkezi"):
            record["summary"] = "Mekteplerin üst düzey öğrenci temsilcilerini buluşturan, okullar arası siyasî ilişkileri ve müzakere süreçlerini düzenleyen merkezî kurum."
            record["content"] = """# Hilalifiyet Merkezi

## Kurumun niteliği
Hilalifiyet Merkezi, Büyük Türk İmparatorluğu'ndaki mekteplerin üst düzey öğrenci temsilcilerini bir araya getiren merkezî müzakere kurumudur. Temsil edilen birimler devletler değil, mekteplerdir. Bu yönüyle diplomatik kuruluşlara benzer; ancak faaliyet alanı öğrenci blokları, okul ittifakları ve gençlik teşkilatlarıdır.

İmparatorluğun her ilinde en az bir merkez bulunur. İstanbul ve Ankara gibi büyük şehirlerde birden fazla merkez faaliyet gösterebilir. Kurum, Kızıl Orda'ya ve Maarif ve Gençlik Nizamı'na bağlıdır.

## İki otorite alanı
Merkezde iki yetki alanı birlikte işler:
- **Öğrenci temsili:** okul başkanları, müzakere heyetleri, ittifaklar ve öğrenci blokları.
- **Devlet denetimi:** merkez bürokrasisi, atanmış uzman jüriler, hukukî denetim ve Ankara'nın gözetimi.

Bu nedenle öğrenci temsilcileri kendi aralarında karar ve ittifak geliştirebilir; ancak kararların yürürlüğe girmesi devletin belirlediği usule bağlıdır.

## Karar süreci
Bir talep önce gerekçelendirilir, ardından jüri tarafından değerlendirilir. Uygun görülen karar idarî onaydan geçtikten sonra bağlayıcı hâle gelir. Nizam-1 bu süreçte analiz ve karşılaştırma desteği sunar; karar veren makam değildir.

## Yetkiler ve yaptırımlar
Hilalifiyet Merkezi; ittifaklara katılma, liderlik tanıma, bütçe ve araştırma imtiyazları, yarışma hakları ve müzakere ayrıcalıkları gibi konuları düzenleyebilir. Temsilin askıya alınması, oy hakkının kısıtlanması veya bazı imtiyazların geri alınması da yaptırımlar arasındadır.

Rekabet serbesttir; fakat devlet güvenliğini tehdit ettiği kabul edilen eylemler bu serbestinin dışındadır. Böylece merkez, öğrencilere siyasî deneyim kazandırırken gençlik örgütlerini devlet denetimi altında tutar.

## 1985 gündemi
16 Eylül 1985'te düzenlenen Mektepler Arası Teknoloji Tasarım Yarışması, kurumun o yılki en görünür faaliyetlerinden biridir. Üsküdar ve Şarkın mektepleri arasındaki rekabet, öğrenci liderlerinin güç dengelerini ve devletin gençlik politikasını aynı sahnede buluşturur."""
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

    # Reconcile legacy summaries with the updated 1985 canon. These reader-facing
    # entries deliberately distinguish established facts from unresolved local detail.
    world_overrides = {
        "Genel Dünya": (
            "1985'te dünya iki egemen karar merkezi çevresinde şekillenir: güneyde Büyük Türk İmparatorluğu, kuzeyde Großdeutsches Reich. Amerika Birleşik Devletleri 1946'da merkezî devlet olarak çökmüştür; üçüncü bir süper güç değildir.",
            """# 1985 Dünya Düzeni

## Tarihin ayrıldığı nokta
Bu evrenin tarihi, 10 Kasım 1938'de Atatürk'ün vefatıyla farklı bir yola girer. 29 Kasım 1938'de Alperen Keser yönetimi devralır. Yeni yönetim merkezî idareyi, millî sanayiyi ve askerî hazırlığı güçlendirir. Türkiye'nin savaş yıllarındaki yönelişi, Sovyetler Birliği'nin 1943'te çöküşü ve 1946'daki dünya paylaşımı bu tek tarih kırılmasının sonuçlarıdır.

## Savaş ve güç dengesi
1940'ta Fransa ve İngiltere'nin düşmesi Avrupa'daki dengeyi değiştirir. 1941–1943 arasında Almanya ve Türkiye'nin Sovyetler Birliği'ne karşı yürüttüğü savaş, Sovyet merkezî bütünlüğünün sona ermesiyle sonuçlanır. 1946'da Amerika'nın çöküşüyle savaş sonrası güç boşluğu iki imparatorluk arasında paylaşılır.

## İki egemen merkez
1985'te dünya iki büyük karar merkezine ayrılmıştır:
- **Büyük Türk İmparatorluğu:** Ankara merkezli güney düzeni. Anadolu, Balkanlar ve Viyana, Kafkasya, Türkistan, Ortadoğu, Afrika'nın bazı bölgeleri, Güney Amerika, Antarktika ve Ay programı bu nüfuz alanının parçalarıdır.
- **Großdeutsches Reich:** Germania merkezli kuzey düzeni. Avrupa'nın büyük bölümü, Britanya, İskandinavya, Avrupa Rusyası, Sibirya ve Kuzey Amerika'nın kuzey kuşağı Reich'ın nüfuz alanındadır.

Bu iki merkez dışındaki yapılar bağımsız üçüncü bir süper güç oluşturmaz. Bazı bölgeler doğrudan yönetilir, bazıları koloni veya işgal bölgesidir; bazılarıysa bağlı hanlık, tampon alan ya da eski devletlerden kalan yerel yönetimler biçiminde varlığını sürdürür.

## Amerika'nın durumu
Amerika Birleşik Devletleri 1985'te devlet olarak yoktur. 1946'daki iki atom saldırısı ve okyanus yenilgileri federal yapının çöküşüne yol açmıştır. Eski topraklar kuzey ve güney nüfuz alanlarına ayrılmış; şehirler, yerel topluluklar ve mülteci çevreleri eski Amerikan kimliğini farklı biçimlerde taşımaya devam etmiştir.

## İki rejimin niteliği
Büyük Türk İmparatorluğu otoriter-milliyetçi bir devlettir; Großdeutsches Reich ise Nazi rejimidir. Bu ayrım, Türk devletinin masum olduğu anlamına gelmez. İmparatorluğun da infaz, sürgün, zorla teslim ve taşrada keyfî yönetim gibi ağır sorumlulukları vardır. Romanın siyasî dünyası, iki rejimin gücünü olduğu kadar bu gücün insanlara yüklediği bedeli de gösterir.

## Teknoloji ve gündelik hayat
1985 teknolojisi kendi tarihimizin 1985'inden ileridir; ancak 2000'lerin başındaki tüketici teknolojisine ulaşmaz. Jet uçakları, bilgisayarlar, uydu haberleşmesi ve nükleer enerji kullanılır; internet ve yaygın cep telefonu yoktur. Türk araştırmaları sensör, uzay ve uçan kanat havacılığına; Reich araştırmaları füze, yüksek enerji fiziği ve antimadde alanlarına ağırlık verir.

## Romanın anlatı odağı
Dünya tarihi, Oğuz'un hayatından bağımsız bir arka plan değildir. Oğuz geçmişi büyük ölçüde ailesinden, özellikle dedesinin anlattıklarından öğrenir. Bu nedenle resmî tarih ile ev içinde aktarılan hatıralar zaman zaman birbirini tutmaz; okur dünyayı hem devlet kayıtlarından hem de karakterlerin yaşadıklarından tanır."""
        ),
        "Dünya Paylaşımı 1946": (
            "Amerika'nın merkezî devlet olarak çökmesinden sonra Almanya ve Türkiye arasında kurulan kuzey-güney nüfuz paylaşımı. İlke: Kuzey Almanya'nın, güney Türkiye'nin.",
            """# 1946 — Dünya Paylaşımı

## Paylaşımın nedeni
1946'da Amerika Birleşik Devletleri'nin merkezî yönetimi çöktüğünde, savaşın sonunda ortaya çıkan güç boşluğu Almanya ve Türkiye'nin etkisiyle yeniden düzenlendi. İki heyet, Germania'daki Große Halle'de eski Amerikan topraklarının ve diğer nüfuz alanlarının paylaşımını görüştü.

## Temel ilke
Paylaşımın kısa formülü **“Kuzey Almanya'nın, güney Türkiye'nin”** oldu. Sınırlar doğal, etnik veya tarihî bütünlüğe göre çizilmedi. Harita, iki imparatorluğun stratejik çıkarları ve güç dengesi temelinde cetvelle bölündü.

## Reich'ın kuzey alanı
Almanya; Kanada'yı, Alaska'yı, Grönland'ı, Kuzey Amerika'nın kuzey ve orta kuşağını, Avrupa'nın büyük bölümünü, Britanya'yı, İskandinavya'yı, Avrupa Rusyası'nı ve Sibirya hattını kendi düzenine bağladı.

## Türk güney alanı
Türkiye; Meksika, Orta Amerika, Karayip geçişleri ve Güney Amerika'nın yanı sıra Ortadoğu, Kafkasya, Türkistan, Balkanlar, Viyana, Afrika'nın doğu ve güney kuşakları ile güney deniz bağlantılarında nüfuz kazandı.

## Bölünmüş ve ortak alanlar
İtalya tek parça hâlinde bir tarafa bırakılmadı: kuzeyi Alman, güneyi ve Akdeniz adalarının bir bölümü Türk nüfuzunda kaldı; Roma ortak yönetim alanı olarak düzenlendi. Eski ABD'nin bazı güney bölgeleri ise tampon veya ortak ekonomik alan niteliği taşıdı. Bu statüler, doğrudan ilhakla aynı şey değildir.

## Sonuç
1946 paylaşımı yeni düzenin temelini kurdu; 1947–1950 arasında ilhaklar, bağlı yönetimler ve sınır düzenlemeleri devam etti. **1950'de İstanbul'da** Yeni Dünya Düzeni ilan edildi ve Büyük Türk İmparatorluğu ile Großdeutsches Reich adları resmîleşti."""
        ),
        "Türkiye": (
            "Büyük Türk İmparatorluğu, 1950'de İstanbul'da resmen ilan edilen, Ankara merkezli otoriter-milliyetçi güney imparatorluğudur.",
            """# Büyük Türk İmparatorluğu

## Kuruluş çizgisi
10 Kasım 1938'de Atatürk'ün vefatından sonra, 29 Kasım 1938'de Alperen Keser yönetimi devralır. Yeni yönetim merkezî devleti, sanayileşmeyi ve askerî hazırlığı ön plana çıkarır. 1946 dünya paylaşımıyla yeni nüfuz alanı şekillenir; 1950'de İstanbul'da Büyük Türk İmparatorluğu adı resmen ilan edilir.

## Yönetim
1985'te devletin başında Ulu Han Selim Arkan bulunur. Başkent Ankara'dır. Ulu Han'ın iradesini resmî ve bağlayıcı emirlere dönüştüren Başbuyruk makamı, merkezî bürokrasinin temel parçalarındandır. Nazırlıklar, askerî kurumlar ve istihbarat teşkilatları geniş imparatorluk alanını yönetir.

## Toprakların yönetimi
İmparatorluğun bütün bölgeleri aynı statüde değildir. Anadolu ve bazı çekirdek bölgeler doğrudan vilayet düzeniyle yönetilir. Uzak coğrafyalarda umumi valilikler bulunur. Buhara, Hive ve Hicaz gibi bağlı hanlıklar ise iç işlerinde belirli ölçüde serbest, dış ilişkilerinde Ankara'ya bağlıdır. Bu farklılıklar, geniş coğrafyayı tek merkezden yönetmenin siyasî ve idarî zorluklarını gösterir.

## Toplum ve kurumlar
Eğitim ve gençlik siyaseti devletin doğrudan ilgilendiği alanlardır. Kanat sistemi öğrencilerin okul içindeki sorumluluk ve temsil düzeylerini belirler; Hilalifiyet Merkezleri ise mektepler arasında müzakere ve öğrenci siyaseti için kurumsal alan oluşturur.

## Devletin ahlakî yükü
İmparatorluk kendisini Nazi Reich'ından farklı tanımlar ve ideolojik olarak otoriter-milliyetçi bir çizgidedir. Ancak bu fark onu masum kılmaz. Savaş yıllarında işlenen infazlar, sürgünler, zorla teslimler ve taşrada süren keyfî uygulamalar, devletin resmî düzen anlatısının altında duran gerçek sorumluluklardır."""
        ),
        "Almanya": (
            "Großdeutsches Reich, 1985'te kuzey nüfuz alanını yöneten Nazi imparatorluğudur; merkezi Germania'dır.",
            """# Großdeutsches Reich

## Devletin konumu
Großdeutsches Reich, 1985'te Avrupa ve kuzey nüfuz alanlarının merkezinde bulunan Nazi rejimidir. Yönetimin başında Führer und Reichskanzler Reinhard Falkenhorst yer alır. Reich'ın siyasî düzeni parti, SS, ordu ve sanayi çevrelerinin iç rekabeti üzerine kuruludur.

## Yönetim ve baskı
Parti teşkilatı atamaları ve ideolojik disiplini yürütür; SS ve güvenlik aygıtı rejimin gözetim ve baskı düzenini uygular; ordu ve sanayi ise devletin askerî ve ekonomik gücünü taşır. Bu kurumlar arasında rekabet bulunması, Reich'ın otoriter ve Nazi niteliğini değiştirmez.

## Türkiye ile ilişkiler
Türkiye ile geçmişteki ittifak, savaş sonrasında çıkar ve güç rekabetine dönüşmüştür. Diplomatik heyetler ve teknik temaslar sürse de iki taraf birbirinin havacılık, sensör, bilim ve stratejik kapasitesini yakından izler. Açık dostluk söyleminin altında karşılıklı güvensizlik bulunur.

## Bilim ve teknoloji
Reich füze, ağır zırh, yüksek enerji fiziği ve antimadde araştırmalarına ağırlık verir. SFA-P Polaris, bu araştırmaların önemli merkezlerinden biridir. Türk bilim çevreleriyle arasındaki fark yalnızca teknik önceliklerden değil, bilinmeyen doğa olaylarına yaklaşım biçiminden de kaynaklanır.

## Koloniler ve bağlı alanlar
Reich'ın Avrupa dışındaki nüfuz alanları tek tip değildir. Bazı bölgeler doğrudan yönetilir, bazıları koloni veya işgal düzenindedir. Yerel kimlikler ve direniş çevreleri varlığını sürdürür; geniş coğrafyanın idaresi rejim için sürekli bir yük oluşturur."""
        ),
        "Amerika": (
            "Amerika Birleşik Devletleri 1946'da merkezî devlet olarak çökmüştür; 1985'te bağımsız Amerikan devleti veya üçüncü dünya kutbu yoktur.",
            """# Eski Amerika Birleşik Devletleri

## 1946 öncesi konum
Avrupa'daki Mihver ilerleyişi, İngiltere'nin düşüşü ve Sovyetler Birliği'nin parçalanması Amerika'yı giderek yalnızlaştırdı. Buna rağmen Amerika, 1946'ya kadar denizaşırı büyük güç olarak varlığını sürdürdü.

## Ağustos 1946
**1 Ağustos 1946'da Washington, D.C. Türkiye'nin atom saldırısına uğradı.** Bu saldırı federal yönetimi ağır biçimde sarstı. **8 Ağustos 1946'da New York'a Almanya tarafından ikinci saldırı düzenlendi.** İki darbe, daha önceki okyanus yenilgileriyle birlikte merkezî devlet yapısının çöküşünü hızlandırdı.

## Toprakların paylaşılması
Amerika'nın kuzey ve orta bölgeleri Reich'ın nüfuz alanına; Meksika, Orta Amerika ve daha güneydeki alanlar Türk nüfuzuna girdi. Bazı eski eyaletler tampon veya ortak ekonomik alan olarak düzenlendi. Bu bölgelerin hepsi aynı idarî statüde değildir.

## 1985'te Amerika ne demektir?
1985 yılında Amerika Birleşik Devletleri bağımsız bir devlet olarak mevcut değildir. Eski Amerikan topraklarında koloniler, bağlı yönetimler, yerel topluluklar, direniş çevreleri ve göçmen hafızası bulunur. Washington ve New York tarihî önemlerini korur; ancak eski federal devletin işleyen başkentleri değildir."""
        ),
        "Diğer Devletler": (
            "İtalya bölünmüş ve Roma ortak yönetimlidir; Japonya ikincil/bağlı aktördür. İngiltere, Fransa ve Sovyet sonrası bölgeler eski devlet statülerini kaybetmiştir.",
            """# Diğer Devletler ve Eski Güçler

## İtalya
İtalya tek bir imparatorluğa bütünüyle bağlanmış değildir. Kuzey kesimi Alman, güneyi ve Akdeniz adalarının bir bölümü Türk nüfuzundadır. Roma ortak yönetim alanı olarak korunmuştur. Bu paylaşım, ülkenin siyasî bütünlüğünü ortadan kaldırırken sembolik başkent statüsünü ayrı tutar.

## Japonya
Japonya Pasifik'te varlığını ve bölgesel etkisini korur; ancak 1985 dünya düzeninin üçüncü egemen kutbu değildir. Yeni düzenin ana karar merkezleri Almanya ve Türkiye'dir.

## İngiltere ve Fransa
İngiltere'nin 1940'ta düşmesi Britanya İmparatorluğu'nun eski sömürge ağını parçalamıştır. Fransa da 1940 yenilgisinin ardından eski denizaşırı konumunu kaybetmiştir. Her iki halkın kimliği ve direniş hafızası devam eder; fakat eski küresel devlet güçleri ortadan kalkmıştır.

## Sovyet sonrası coğrafya
1943'te Sovyet merkezî yapısının çöküşünden sonra kuzey ve doğu bölgelerinde bağlı yönetimler, işgal alanları ve yerel direniş yapıları ortaya çıkmıştır. Bu bölgeler tek bir bağımsız Sovyet ardılı devlet altında birleşmez."""
        )
    }
    for record in records:
        override = world_overrides.get(record.get("title"))
        if override:
            record["summary"], record["content"] = override

    records += public_folder_nodes("geography", "Alternatif Tarih/Dünya/Coğrafya")
    for record in records:
        if normalize(record.get("title", "")).replace("—", "").strip() == "istanbul 1985 sehir profili":
            record["summary"] = "İstanbul, 1985 anlatısındaki iki ayrı mektebin ve öğrenci çevresinin bulunduğu şehirdir; B-3 Üsküdar Mektebi'ndedir."
            record["content"] = """# İstanbul — 1985 Şehir Profili

İstanbul, romanın genç karakterlerinin okul ve aile yaşamının geçtiği başlıca şehirdir. Anlatıda iki ayrı mektep önem taşır:

- **Üsküdar Milli İlim ve İrfan Mektebi:** Oğuz Kağan Atalay ve B-3 sınıfının bulunduğu okul. Alper Ulaç Altaylı okul başkanı, İsmail Yağız Aslan başkan yardımcısıdır.
- **İstanbul Şarkın İlim ve Teknoloji Mektebi:** Tomris İlter ve Asena Korkut'un öğrenim gördüğü ayrı okul. Tomris okul başkanı, Asena başkan yardımcısıdır.

Bu iki okulun öğrenci kadroları birbirine karıştırılmamalıdır. Aralarındaki rekabet ve Hilalifiyet çevresindeki ilişkiler, gençlerin hikâyelerini birbirine bağlar.

İstanbul'un alternatif evrendeki 1985 idarî bölünümü, okul kampüslerinin kesin adresleri ve ayrıntılı ulaşım bağlantıları mevcut kamusal kayıtlarda bütünüyle sabitlenmemiştir. Bu nedenle doğrulanmamış ilçe veya adres bilgisi eklenmez."""
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

    technology_overviews = [
        {
            "title":"Türk Teknolojileri — 1985 Genel Bakış",
            "path":"Alternatif Tarih/Teknoloji/Türk teknolojileri/1985 Türk Teknolojileri.md",
            "sourceName":"Türk Teknolojileri",
            "summary":"İmparatorluğun güçlü olduğu alanlar havacılık, sensör füzyonu, ölçüm sistemleri ve uzay çalışmalarıdır; bazı ileri fizik ve malzeme alanlarında Reich'a bağımlılık sürer.",
            "country":"turkish",
            "content":"""# Türk Teknolojileri — 1985 Genel Bakış

## Havacılık
Türk uçan kanat çizgisi 1958'deki Ta 70 prototipinden 1975'te seri üretime geçen Ta 85 Gökkanat'a uzanır. Gökkanat, yalnızca bir uçak projesi değil, imparatorluğun stratejik havacılık kimliğinin simgesidir. Atalay ailesinin üç kuşağı da bu programla farklı biçimlerde bağlantılıdır: Necdet ve Cengiz mühendislik tarafında, Oğuz ise pilotluk hedefiyle yer alır.

## Zırhlı araçlar ve arşiv teknolojisi
Türk Panzeri, ağır ve dayanıklı zırhlı araç serisini temsil eder. Tarih Bombası adı verilen program ise fiziksel bir patlayıcıdan ziyade belge ve arşiv kayıtlarının değiştirilmesiyle ilgilidir. Bu nedenle programın etkisi cepheden çok devlet hafızası, tarih yazımı ve güvenilir kayıtlar üzerinde hissedilir.

## Sensör ve ölçüm
Gök Kutup'un araştırma çizgisi, farklı ölçüm türlerini bir araya getirerek çevresel ve fiziksel değişimleri izlemeye dayanır. Öte-İz Ölçeri, Tunç Halka ve Dokuma gibi sistemler bu araştırma dünyasının adlarıdır. Bu araçların okur açısından önemi, imparatorluğun bilimsel gözlem ve ölçüm kapasitesini temsil etmeleridir.

## Hesaplama ve karar desteği
Nizam-1, Hilalifiyet Merkezi'nde kullanılan mantık ve karar destek bilgisayarıdır. Verileri karşılaştırır ve analiz sunar; ancak siyasî veya idarî kararı kendisi vermez. Ana Beyin ise daha geniş araştırma ve uzay programlarının hesaplama altyapısını temsil eder. Bu iki sistem birbirinin yerine geçmez.

## Uzay programı
Ay programı üç aşamada ilerlemiştir: ilk aşamada insansız görevler, ikinci aşamada geri dönüşlü kapsül çalışmaları, üçüncü aşamada ise mürettebatlı dönüş ve kalıcı üs hedefi öne çıkar. 1985, bu üçüncü aşamanın devam ettiği dönemdir.

## Sınırlar ve bağımlılıklar
İmparatorluk sensör sistemleri, yazılım ve uzay araştırmalarında Reich'ı bazı alanlarda geride bırakmıştır. Buna karşılık ileri fizik, belirli malzemeler ve motor ömrü gibi konularda eksikleri sürer. Bu nedenle iki devlet arasındaki teknoloji ilişkisi tek yönlü bir üstünlük değil, alanlara göre değişen rekabet ve bağımlılık ilişkisidir."""
        },
        {
            "title":"Alman Teknolojileri — 1985 Genel Bakış",
            "path":"Alternatif Tarih/Teknoloji/Alman Teknolojileri/1985 Alman Teknolojileri.md",
            "sourceName":"Alman Teknolojileri",
            "summary":"Reich; füze ve roket sistemleri, ağır sanayi, yüksek enerji fiziği ve antimadde araştırmalarında güçlüdür; sensör füzyonu, yazılım ve uzay lojistiğinde Türkiye'nin gerisindedir.",
            "country":"german",
            "content":"""# Alman Teknolojileri — 1985 Genel Bakış

## Havacılık
Horten 229, Reich'ın uçan kanat tasarım çizgisinin simgesidir. 1940'ların prototiplerinden 1960'lardaki modernizasyonlara, oradan 1980'lerin B/C serisine uzanan bir gelişim hattı vardır. Gökkanat ile aynı tasarım ailesi fikrini paylaşsa da iki projenin tarihî ve kurumsal geçmişi farklıdır.

## Sivil havacılık
Me 620 Überschall, Reich'ın süpersonik yolcu uçağı programıdır. Devlet prestijini ve yüksek hızlı sivil taşımacılık iddiasını temsil eder. Kanona göre askerî türevi bulunmaz; bu nedenle onu savaş uçağı olarak tanıtmak yanlıştır.

## Atom ve yüksek enerji fiziği
Reich, atom çağında erken teknolojiye erişmiş ve bunu sınırlı sayıdaki stratejik kapasiteye dönüştürmüştür. SFA-P Polaris'teki halka deneyleri, yüksek enerji fiziği ile antimadde ve karanlık madde araştırmalarının bir arada yürütüldüğü bilimsel hattı temsil eder. Deneylerin sonuçları kesin ve güvenli değildir; yüksek enerji araştırmaları önemli bilimsel riskler taşır.

## Füze ve roket araştırmaları
Füze ve roket teknolojileri Reich'ın güçlü olduğu alanlardandır. Bu üstünlük, devletin kıtalararası erişim ve uzay çalışmaları konusundaki iddiasını destekler; ancak tek başına bütün teknoloji alanlarında üstünlük anlamına gelmez.

## Güçlü ve zayıf alanlar
Reich ağır sanayi, füze sistemleri ve yüksek enerji fiziğinde güçlüdür. Buna karşılık sensör füzyonu, yazılım, sistemlerin küçültülmesi ve uzay lojistiği alanlarında Türk araştırmaları öne geçmiştir. İki tarafın rekabeti bu nedenle tek bir “ileri teknoloji” sıralamasına indirgenemez."""
        }
    ]
    existing_titles = {normalize(record.get("title", "")) for record in records}
    for item in technology_overviews:
        if normalize(item["title"]) in existing_titles:
            continue
        doc = {
            "title":item["title"], "summary":item["summary"], "content":item["content"],
            "path":item["path"], "sourceName":item["sourceName"], "aliases":[],
            "country":item["country"]
        }
        records.append(node("technology", doc, "1985 · TEKNOLOJİ GENEL BAKIŞI"))

    for record in records:
        if normalize(record.get("title", "")).startswith("ta 85 gokkanat"):
            record["summary"] = "Türk uçan kanat havacılığının gelişim çizgisi: 1958'de Ta 70 prototipi ve 1975'te TA-85 Gökkanat'ın seri üretime geçmesi."
            record["content"] = """# Ta 70 ve TA-85 Gökkanat — Kamuya Açık Tarihçe

## Projenin yeri
Gökkanat, Büyük Türk İmparatorluğu'nun uçan kanat havacılık çizgisinin en tanınan projelerinden biridir. Sadece bir uçak modeli olarak değil, Necdet Atalay'ın kuşağından başlayıp Cengiz Atalay ve sonraki mühendislerle devam eden uzun bir mühendislik geleneğinin parçası olarak değerlendirilir.

## Gelişim çizgisi
- **1958 — Ta 70:** Türk uçan kanat tasarımının ilk prototip aşaması. Necdet Atalay bu dönemin mühendisleri arasındadır.
- **1975 — TA-85 Gökkanat:** Yeni seri üretim dönemi başlar. 1985'te Gökkanat, imparatorluğun havacılık kimliğinin başlıca simgelerinden biridir.

## Aile belleği
Necdet Atalay'ın çalışmaları, oğlu Cengiz'in askerî uçak mühendisliği kariyeri ve torunu Oğuz'un pilot olma isteği arasında kuşaklar boyunca süren bir bağ kurar. Necdet ve Cengiz uçakların geliştirilmesiyle, Oğuz ise onları uçurmak arzusuyla bu mirasın farklı halkalarını temsil eder. Programın aile içindeki geçmişine ilişkin bazı kayıtlar ise kamuya açık tarihçenin dışında tutulur.

## Kamusal kapsam
Bu kayıt projenin tarihsel gelişimini ve evrendeki yerini açıklar. Tasarım, üretim, performans, silahlandırma veya operasyonel kullanıma yönelik uygulanabilir teknik ayrıntı içermez."""
            record["country"] = "turkish"
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
        if normalize(record.get("title", "")) == "b 3 sinif profili":
            record["summary"] = "Oğuz, Alper, İsmail, Muhammed Mete, Aylin ve Alev'in 1985 yılında öğrenim gördüğü Üsküdar Milli İlim ve İrfan Mektebi sınıfı."
            record["content"] = """# B-3 Sınıf Profili — Üsküdar Milli İlim ve İrfan Mektebi

## Sınıfın yeri
B-3, 1985 eğitim yılında Üsküdar Milli İlim ve İrfan Mektebi'nde bulunan 3. sınıf B şubesidir. Akademik seviyesi yüksek olmakla birlikte öğrencileri tek tip değildir; teknik merak, hukuk, siyaset, liderlik ve sosyal beceriler aynı sınıf çevresinde buluşur.

## Öğrenci kadrosu
- **Oğuz Kağan Atalay:** Üç kanatlıdır. Havacılığa ve teknik sistemlere ilgi duyar; askerî pilot olmak ister.
- **Alper Ulaç Altaylı:** Altı kanatlı okul başkanıdır. Öğrenci ilişkilerini ve okul içindeki bilgi akışını yönetir.
- **İsmail Yağız Aslan:** Beş kanatlı başkan yardımcısıdır. Rahat ve esprili tavrının altında güçlü bir pratik zekâ bulunur.
- **Muhammed Mete:** Dört kanatlıdır. Sakin ve uyumlu yapısıyla grupta denge kurar; sivil pilotluğu hedefler.
- **Aylin Aksoy:** Üç kanatlıdır. Gözlemci ve planlıdır; hukuk alanına yönelmek ister.
- **Alev Acar:** İki kanatlıdır. Enerjik ve uyumludur; sivil pilot olmak ister.

## Şarkın Mektebi ile ayrım
Tomris İlter ve Asena Korkut bu sınıfın öğrencileri değildir. İkisi de **İstanbul Şarkın İlim ve Teknoloji Mektebi**'nde öğrenim görür. Tomris o okulun altı kanatlı başkanı, Asena beş kanatlı başkan yardımcısıdır. İki mektep arasındaki rekabet ve öğrenci temsil ilişkileri genç karakterlerin hikâyelerini birbirine bağlar.

## Kanat sistemi
Kanat sayısı öğrencinin okul içindeki sorumluluk ve temsil düzeyini gösterir. Öğretmenler ders, grup çalışması ve davranışları gözlemleyebilir; fakat Kanat seviyesini tek başlarına belirlemez. Nihai işleyiş Kanat Konseyi ve ilgili sistem kuralları üzerinden yürür.

## Sınıfın hikâyedeki yeri
B-3, farklı hedefleri olan gençleri aynı gündelik çevrede buluşturur. Arkadaşlık, rekabet, öğrenci siyaseti ve gelecek beklentileri burada iç içe geçer. Bu nedenle sınıf, romanın genç karakterlerinin birbirini tanıdığı ve kararlarının birbirini etkilediği temel sosyal alandır."""
        record_path = normalize(record.get("path", ""))
        if record_path == "kanat" or "kanat sistemi" in normalize(record.get("title", "")):
            record["country"] = "both"
            record["summary"] = "İmparatorluk genelinde öğrencilerin okul içindeki sorumluluk, temsil ve görev kapsamını altı seviyede düzenleyen sistem."
            record["content"] = """# Kanat Sistemi — Kamusal Çerçeve

## Sistemin anlamı
Kanat, öğrencinin zekâsını, servetini veya dokunulmazlığını gösteren bir rütbe değildir. Okul içinde üstlendiği sorumluluğun ve temsil ettiği öğrenci çevresinin kapsamını belirtir. Seviye yükseldikçe yalnızca yetki değil, sorumlu olunan insan sayısı ve hesap verme yükü de artar.

## Altı seviye
| Kanat | Anlamı | Tipik sorumluluk |
|---|---|---|
| 1 | Başlangıç | Kendi görevlerini düzenli yerine getirmek |
| 2 | Güvenilir katkı | Yardım, küçük grup desteği ve temsil |
| 3 | Grup liderliği | Küçük ekipleri yönlendirmek ve sunum yapmak |
| 4 | Organizasyon | Üç kanatlı öğrencilerin koordinasyonuna ve okul işleyişine katkı |
| 5 | Başkan yardımcılığı | Okul temsili ve müzakere heyetinde görev |
| 6 | Okul başkanlığı | Okulun öğrenci siyaseti, temsil ve ittifak kararları |

## Kim belirler?
Öğretmenler öğrencilerin davranış, katkı, grup çalışması ve sorumluluklarını gözlemler; bu gözlemler değerlendirme sürecine bilgi sağlar. Kanat seviyesini öğretmenler tek başına vermez. Karar, öğrenciler ve danışman öğretmenin yer aldığı Kanat Konseyi'nin kuralları üzerinden yürür. Maarif ve Gençlik Nizamı ile Hilalifiyet sicil düzeni sistemi denetler.

## Sınırlar
Kanat sayısı ayrıcalık veya dokunulmazlık sağlamaz. En yüksek seviyedeki okul başkanı da ağır ihlal durumunda görevden alınabilir. Sistem resmî söylemde liyakat ve sorumluluk ilkelerine dayanır; uygulamada kayırmacılık ve oy ilişkileri etrafında tartışmalar yaşanabilir."""

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
