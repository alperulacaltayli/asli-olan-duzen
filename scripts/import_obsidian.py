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

def make_public_character(category, spec):
    """Create a short, spoiler-safe character card from an approved source note."""
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
            "date":"1945 · 40 yaş", "birth":"1945", "age":"40",
            "role":"Askerî uçak mühendisi",
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
            "date":"1888–1960", "birth":"1888 · Giresun, Kuşköy",
            "role":"Asker ve devlet adamı · 1938–1960 döneminin lideri",
            "personality":"Disiplinli, kararlı, milliyetçi ve güçlü merkezi devlet yanlısı.",
            "aliases":["Alperen","Alperen Keser"]
        },
        {
            "key":"ismail-karaslan", "path":political_base+"İsmail Karaslan.md", "name":"İsmail Karaslan",
            "date":"1904 doğumlu · 1960–1975 döneminde lider",
            "birth":"1904 · Hatay",
            "role":"Asker ve devlet adamı",
            "personality":"Disiplinli, devletçi, temkinli ve güçlü merkezi yönetim yanlısı.",
            "aliases":["İsmail Karaslan"]
        },
        {
            "key":"selim-arkan", "path":political_base+"Selim Arkan.md", "name":"Selim Arkan",
            "date":"1935 doğumlu · 1975'ten itibaren lider",
            "birth":"1935 · Ankara",
            "role":"Siyasetçi ve devlet adamı",
            "personality":"Soğukkanlı, pragmatik, devletçi ve stratejik düşünen.",
            "aliases":["Selim Arkan"]
        },
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

    def collect(keys, source):
        return [source[key] for key in keys if key in source]

    young_people = make_character_group(
        "Genç karakterler", "GENÇ KARAKTERLER",
        "1985 yılında hikâyenin genç kuşağını oluşturan öğrenciler ve arkadaş çevresi.",
        collect(["alev-acar","asena-korkut","aylin-aksoy","tomris-ilter",
                 "ismail-yagiz-aslan","muhammed-mete"], main_nodes),
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
        "Devlet liderleri", "SİYASİ KARAKTERLER",
        "Keser soy ağacının dışında yer alan devlet yöneticileri.",
        collect(["ismail-karaslan","selim-arkan"], political_nodes),
        "state-leaders"
    )

    roots = [young_people, atalay_suyu, keser_soyu, state_leaders]
    roots = [item for item in roots if item.get("children")]
    if not roots:
        return None

    return {
        "id":"characters",
        "title":"Karakterler",
        "description":"Kısa, genel ve spoilersız karakter tanıtımları. Aile bağları ayrı soy ağaçlarında düzenlenmiştir.",
        "view":"tree",
        "label":"KARAKTER VE SOY AĞAÇLARI",
        "order":3,
        "nodes":roots
    }

def public_folder_nodes(category, relative_folder):
    """Import only explicitly approved, public Markdown notes from an author folder."""
    folder = VAULT / relative_folder
    if not folder.is_dir():
        return []
    records = []
    for path in sorted(folder.rglob("*.md"), key=lambda item: item.as_posix().casefold()):
        if path.name.casefold() in {"readme.md", "index.md"}:
            continue
        relative = path.relative_to(VAULT).as_posix()
        raw_head = path.read_text(encoding="utf-8-sig")[:1800]
        status = re.search(r"(?mi)^status\s*:\s*(onaylandı|onaylandi|approved|established canon)\s*$", raw_head)
        visibility = re.search(r"(?mi)^(?:visibility|publication|yayın)\s*:\s*(public|kamuya açık|herkese açık)\s*$", raw_head)
        if not status or not visibility:
            continue
        doc = read_doc(relative)
        if doc:
            records.append(node(category, doc, str(doc.get("date", ""))))
    return records

def import_institutions():
    specs = [
        "Kuruluşlar/Hilalifiyet Merkezi - İstanbul.md",
        "Aslı Olan Düzen/World/Organizations/Turkish Empire/Kızıl Orda.md",
    ]
    records = []
    for rel in specs:
        doc = read_doc(rel)
        if doc:
            records.append(node("institutions", doc))
    records += public_folder_nodes("institutions", "Kuruluşlar/Kamuya Açık")
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
        "description":"Alternatif dünyanın güç alanları, devlet profilleri ve 1946 paylaşımının coğrafi çerçevesi. Ayrıntılı şehir ve bölge haritaları yeni atlas dosyaları geldikçe genişler.",
        "view":"catalogue",
        "label":"COĞRAFYA VE SİYASİ ATLAS",
        "order":2,
        "nodes":records
    }

def import_technology():
    rel = "Alternatif Tarih/Karakterler/Ana ve Destek Karakterler/Necdet Atalay.md"
    doc = read_doc(rel)
    if not doc:
        return None
    entry = {
        "id":"technology-ta-85-gokkanat",
        "path":rel,
        "sourceName":"TA-85 Gökkanat",
        "title":"TA-85 Gökkanat",
        "date":"Prototip dönemi: 1943",
        "summary":"Türk uçan kanat tipi bombardıman uçağı projesi.",
        "content":"**TA-85 Gökkanat**, evrende yer alan Türk uçan kanat tipi bombardıman uçağı projesidir. Necdet Atalay'ın karakter dosyası, uçağın yapımında görev aldığını kaydeder. Bu katalog yalnızca genel ve yayımlanabilir tarihçe bilgisini içerir; uygulamalı teknik ayrıntı veya gizli dosya aktarılmamıştır.",
        "order":1,
        "aliases":["Gökkanat","TA-85"],
        "children":[],
        "links":[]
    }
    records = [entry]
    records += public_folder_nodes("technology", "Alternatif Tarih/Teknoloji/Kamuya Açık")
    return {
        "id":"technology",
        "title":"Teknoloji",
        "description":"Evrenin araç ve teknoloji projelerine ait yayımlanabilir genel kayıtlar.",
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
    records += public_folder_nodes("society", "Aslı Olan Düzen/Toplum ve Gündelik Hayat")
    return {
        "id":"society",
        "title":"Toplum ve Gündelik Hayat",
        "description":"Eğitim düzeni, Kanat sistemi ve 1985 toplum hayatına dair mevcut kayıtlar. Konut, tüketim, çalışma hayatı ve gündelik alışkanlıklar yeni dosyalarla tamamlanacaktır.",
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
        records.append(node("media", press_doc, "10 KASIM 1940"))
    records += public_folder_nodes("media", "Medya ve Basın")
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

def manual_categories():
    root=ROOT/"content"/"archives"
    categories=[]
    reserved={"chronology","world","characters","institutions","technology","geography","society","media","documents"}
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
    for fn in [import_chronology,import_geography,import_characters,import_institutions,import_technology,import_society,import_media,import_documents]:
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
