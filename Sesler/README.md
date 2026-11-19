# AOD Ses Arsivi

Ses dosyalarini bu klasorun altinda ulke ve kayit turune gore duzenle.

## Onerilen klasor duzeni

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

## Desteklenen ses bicimleri
- MP3
- WAV
- OGG / OGA
- M4A / AAC
- FLAC
- OPUS

Dosyalar klasorlerden otomatik bulunur. Yolunda Türk/Türkiye ibaresi bulunan dosyalar Türk arşivine, Alman/Almanya/German/Deutsch ibaresi bulunan dosyalar Alman arşivine atanir.

## Baslik ve aciklama

`_metadata.json` dosyasinda her kaydi goreli dosya yoluyla tanimlayabilirsin:

```json
{
  "audio": {
    "Marşlar/Türklerin Marşları/Ornek.mp3": {
      "title": "Ornek Mars",
      "country": "turkish",
      "category": "Marşlar",
      "subcategory": "Türklerin Marşları",
      "description": "Kayit aciklamasi.",
      "date": "1985",
      "order": 1
    }
  }
}
```

`country` degeri `turkish` veya `german` olabilir. Metadata girilmezse baslik dosya adindan, kategori klasor adindan belirlenir.

Not: Tarayici uyumlulugu icin MP3 (MPEG) ve AAC/M4A bicimleri genis desteklidir.
