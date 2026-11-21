# AOD Ses Arşivi

Ses dosyalarını bu klasörün altında ülke ve kayıt türüne göre düzenle. Site, ses dosyalarını klasörlerden otomatik bulur; başlık, ülke, tür ve metin gibi ek bilgiler `_metadata.json` üzerinden yönetilir.

## Önerilen klasör düzeni

```text
Sesler/
├── Marşlar/
│   ├── Türklerin Marşları/
│   └── Almanların Marşları/
├── Devlet Kayıtları/
│   ├── Türkiye/
│   └── Almanya/
└── Sesler/
    ├── Türkiye/
    └── Almanya/
```

## Desteklenen ses biçimleri

- MP3
- WAV
- OGG / OGA
- M4A / AAC
- FLAC
- OPUS

## Yeni kayıt ekleme

1. Ses dosyasını uygun klasöre koy.
2. `Sesler/_metadata.json` dosyasındaki `audio` nesnesine yeni bir kayıt ekle.
3. Anahtar olarak `Sesler/` klasörüne göreli dosya yolunu kullan.
4. `python scripts/build_site.py` komutunu çalıştır. Katalog ve yayın klasörü otomatik güncellenir.

Örnek: `Sesler/Marşlar/Türklerin Marşları/Yeni Marş.mp3` dosyası için:

```json
{
  "audio": {
    "Marşlar/Türklerin Marşları/Yeni Marş.mp3": {
      "title": "Yeni Marş",
      "country": "turkish",
      "category": "Marşlar",
      "subcategory": "Türklerin Marşları",
      "archive_type": "marches",
      "description": "Kayıt hakkında kısa bilgi.",
      "date": "1985",
      "language": "tr",
      "lyrics": "İlk söz satırı.\nİkinci söz satırı.\n\nYeni kıta.",
      "performer": "Seslendiren",
      "composer": "Besteci",
      "lyricist": "Söz yazarı",
      "order": 2
    }
  }
}
```

## Metadata alanları

| Alan | Gerekli mi? | Açıklama |
|---|---|---|
| `title` | Önerilir | Ziyaretçiye gösterilecek başlık |
| `country` | Önerilir | `turkish` veya `german` |
| `category` | Önerilir | Marşlar, Devlet Kayıtları veya Sesler |
| `subcategory` | İsteğe bağlı | Katalogdaki alt grup |
| `archive_type` | İsteğe bağlı | `marches`, `state` veya `sounds`; boş bırakılırsa kategoriden belirlenir |
| `description` | İsteğe bağlı | Kayıt açıklaması |
| `date` | İsteğe bağlı | Kayıt veya olay tarihi |
| `lyrics` | İsteğe bağlı | Marş/şarkı sözleri; satır sonları korunur ve ziyaretçiye açılır metin olarak sunulur |
| `transcript` | İsteğe bağlı | Konuşma veya ses kaydının yazılı dökümü |
| `performer` | İsteğe bağlı | Seslendiren |
| `composer` | İsteğe bağlı | Besteci |
| `lyricist` | İsteğe bağlı | Söz yazarı |
| `credits` | İsteğe bağlı | Diğer kaynak veya yapım bilgileri |
| `language` | İsteğe bağlı | Kayıt dili |
| `order` | İsteğe bağlı | Aynı arşiv içindeki sıralama |

`lyrics` ve `transcript` alanları zorunlu değildir. Metni olmayan kayıtlar normal ses kaydı olarak listelenir; metin girilen kayıtların kartında ziyaretçi için açılır bir okuma bölümü görünür. Metin alanı HTML olarak çalıştırılmaz, güvenli düz metin olarak gösterilir.

## Otomatik sınıflandırma

- `country`: `turkish` veya `german` kullan. Belirtilmezse klasör adındaki Türk/Türkiye veya Alman/Almanya/German/Deutsch ifadeleri dikkate alınır.
- `archive_type`: `marches` marşlar, `state` resmî/devlet kayıtları, `sounds` ortam ve diğer sesler içindir.
- Metadata girilmezse başlık dosya adından, kategori klasör adından belirlenir.

Yeni ses dosyalarını ekledikten sonra derleme komutunu çalıştırmak yeterlidir; `audio.json` elle düzenlenmez, derleme tarafından yeniden oluşturulur.
