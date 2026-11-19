# AOD Video Arsivi

Bu klasore galeride oynatilacak video dosyalarini ekle.

## Desteklenen dosyalar
- MP4 (tercihen H.264 video + AAC ses)
- WebM
- OGG / OGV

## Video eklemek
1. Video dosyalarini dogrudan bu klasore koy.
2. Istersen video ile ayni dosya adina sahip bir kapak gorseli ekle (`VideoAdi.jpg`, `.png` veya `.webp`).
3. Baslik, tarih ve aciklama vermek icin `_metadata.json` dosyasini duzenle.

Ornek metadata:
```json
{
  "videos": {
    "Gokkanat-Tanitim.mp4": {
      "title": "Gokkanat Tanitim Filmi",
      "date": "1985",
      "category": "Havacilik",
      "description": "Gokkanat projesinin tanitim kaydi.",
      "poster": "Gokkanat-Tanitim.jpg",
      "order": 1
    }
  }
}
```

Metadata zorunlu degildir. Desteklenen video dosyalari otomatik bulunur; metadata girilmezse dosya adi baslik olarak kullanilir.
