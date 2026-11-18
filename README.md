# Aslı Olan Düzen — Dijital Evren Arşivi

Alper Ulaç ALTAYLI'nın **Aslı Olan Düzen** adlı alternatif tarih romanı ve kurgusal evreni için hazırlanan resmî tanıtım ve arşiv sitesi.

## Siteyi yerelde açma

1. Depoyu GitHub Desktop ile bilgisayarına klonla.
2. Proje klasöründe terminal aç.
3. `python scripts/build_site.py` komutunu çalıştır.
4. `python -m http.server 8000 --directory dist` komutunu çalıştır.
5. Tarayıcıda `http://localhost:8000` adresini aç.

## Arşivleri dosyalardan yönetme

Bütün arşiv verileri `content/archives/` klasörünün içindedir. Site, bu klasörleri ve içlerindeki Markdown / TXT dosyalarını okuyarak arşiv arayüzünü üretir.

### Yeni bir kronoloji olayı eklemek

Örnek yapı:

```text
content/
  archives/
    chronology/
      _archive.json
      1938/
        index.md
        ataturkun-vefati.md
        yeni-olay/
          index.md
          alt-olay.md
```

- Bir klasördeki `index.md` veya `index.txt`, o klasörün ana kaydıdır.
- Ana kaydın yanına koyduğun `.md` / `.txt` dosyaları o kaydın alt olayları olur.
- Bir olayın kendi alt dalları olsun istiyorsan, olayla aynı adlı klasör açıp içine `index.md` koy.
- Başlık dosyadaki `title:` alanından veya ilk Markdown başlığından alınır.
- `date:`, `summary:` ve `order:` alanları isteğe bağlıdır.
- Markdown başlığı veya ön bilgi yoksa dosya adı başlık olarak kullanılır.
- TXT dosyasında ilk dolu satır başlık, devamı açıklama olarak yorumlanır.

### Markdown dosyası örneği

```md
---
title: Yeni olayın adı
date: 1940-06-12
summary: Olayın kısa açıklaması.
order: 20
---

# Yeni olayın adı

Olayın ayrıntılı açıklamasını buraya yaz.

- İstersen madde listesi kullan.
- **Kalın** ve *italik* metin desteklenir.
```

Dosyayı kaydettiğinde, sonraki yayın derlemesi klasörleri yeniden tarar. Yeni bir ağaca manuel olarak kod eklemen gerekmez.

## Yeni arşiv türü eklemek

`content/archives/` altında yeni bir klasör oluştur. İçine `_archive.json` koy:

```json
{
  "title": "Coğrafya",
  "description": "Evrenin şehirleri, bölgeleri ve önemli yerleri.",
  "view": "catalogue",
  "label": "COĞRAFİ KAYITLAR",
  "order": 3
}
```

Desteklenen görünümler:

- `tree`: dallanan olay / kayıt ağacı.
- `catalogue`: kartlı katalog.

Sonra aynı klasöre `.md` / `.txt` kayıtları veya `index.md` içeren klasörler ekle.

## Yayınlama sistemi

GitHub Actions, her `main` dalı güncellemesinde `scripts/build_site.py` dosyasını çalıştırır. Betik arşiv klasörlerini tarar, `archives.json` üretir ve siteyi `dist/` klasörüne hazırlar. Ardından GitHub Pages'e yayımlar.

GitHub deposunda **Settings → Pages → Build and deployment → Source** ayarının **GitHub Actions** olması gerekir.

## GitHub Desktop ile çalışma

Windows kurulum ve eşitleme adımları için [GITHUB_DESKTOP.md](GITHUB_DESKTOP.md) dosyasına bak.

## Yayın ilkeleri

- Yalnızca kamuya açık olması onaylanmış eser ve evren bilgileri yayımlanır.
- Yayımlanmamış roman bölümleri, özel notlar ve gizli kanon belgeleri depoya eklenmez.
- Sitede anlatılan alternatif tarih ve evren unsurları kurmacadır.
- Romanın okuma bağlantısı Inkitt üzerindeki eser sayfasına gider.


## Obsidian Vault içe aktarma

Depodaki `AslıOlanDüzenObsidianVault/` klasörü, site derlemesi sırasında belirlenmiş bir izin listesiyle taranır. Her Markdown dosyası otomatik olarak yayımlanmaz.

Şu anda siteye aktarılan bölümler:

- `Tarihi Olaylar/Olaylar/` — yıl bazlı dallanan kronoloji
- `Alternatif Tarih/Dünya/` — ülkeler, dünya paylaşımı ve ülke perspektifleri
- `Alternatif Tarih/Tarih/` — dönem kayıtları
- `Alternatif Tarih/Karakterler/` — karakter profilleri
- `Kuruluşlar/Hilalifiyet Merkezi - İstanbul.md` — kurum kaydı
- `Büyük Türk İmparatorluğu` ve `Kanat` — yerleşik kanon sistem kayıtları
- `TA-85 Gökkanat` — yayımlanabilir genel teknoloji tanıtımı

Obsidian `[[çift köşeli bağlantıları]]` hedef kayıtlar sitede mevcutsa tıklanabilir bağlantıya dönüştürülür. Kronoloji dosyaları yıl ve tarih bilgisine göre gruplandırılır. Kesin tarihi bulunmayan olaylar ayrı tutulur.

### Yayımlanmayan kaynaklar

Taslak, yazar onayı bekleyen, gizli veya büyük hikâye sırrı içeren dosyalar siteye aktarılmaz. Obsidian ayarları, eklenti dosyaları, AI yazım promptları, özel yazım notları ve taslak elçilik/Gök Kutup/Sapma kayıtları yayın derlemesinin dışında tutulur.

Yeni kayıt eklemek için uygun kaynak klasörüne bir Markdown dosyası ekle ve GitHub Desktop üzerinden commit/push yap. Otomatik derleme, izin verilen klasörleri yeniden tarar.

> **Gizlilik uyarısı:** GitHub deposu Public olduğu için `AslıOlanDüzenObsidianVault/` klasörünün içindeki kaynak dosyalar da GitHub'da herkese açıktır. Siteye aktarılmayan bir dosya, depo içinden gizlenmiş olmaz. Özel notları, yayımlanmamış bölümleri ve `.obsidian` ayarlarını ayrı bir private depoda tut.
