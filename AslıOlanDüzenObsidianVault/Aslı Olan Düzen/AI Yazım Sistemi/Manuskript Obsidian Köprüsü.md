# Manuskript Obsidian Köprüsü

Bu not, Manuskript ile Obsidian'ı birlikte kullanma düzenidir.

## Dosya yapısı
- Manuskript proje klasörü: `C:/Users/alper/Desktop/Aslı Olan Düzen/AslıOlanDüzen`
- Manuskript sahneleri: `C:/Users/alper/Desktop/Aslı Olan Düzen/AslıOlanDüzen/outline/`
- Obsidian roman klasörü: `C:/Users/alper/Documents/Obsidian Vault/Aslı Olan Düzen`
- Otomatik bağlam betiği: `C:/Users/alper/Desktop/Aslı Olan Düzen/ai_context_builder.py`
- Üretilen bağlam dosyası: [[Güncel AI Bağlam Paketi]]

## Neden köprü gerekiyor?
Manuskript roman metnini sahne sahne tutuyor. Obsidian ise dünya, karakter, ders, sınıf ve sistem kanonunu tutuyor. AI'nın ileri görüşlü fikir verebilmesi için ikisini aynı anda görmesi gerekir.

## Güncelleme komutu
Git Bash veya Hermes terminalinde:

```bash
cd "/c/Users/alper/Desktop/Aslı Olan Düzen"
python ai_context_builder.py
```

Bu komut iki dosyayı günceller:
- `C:/Users/alper/Desktop/Aslı Olan Düzen/_AI_CONTEXT_BUNDLE.md`
- `C:/Users/alper/Documents/Obsidian Vault/Aslı Olan Düzen/AI Yazım Sistemi/Güncel AI Bağlam Paketi.md`

## Önerilen çalışma akışı
1. Manuskript'te sahneyi yaz.
2. Bağlam betiğini çalıştır.
3. Hermes'e veya ücretsiz/local AI'ya şu dosyayı okut: [[Güncel AI Bağlam Paketi]]
4. [[01 - Roman Fikir Motoru Promptu]] içindeki formatla fikir iste.
5. Karar verilen kanon değişikliklerini Obsidian notlarına ekle.
6. Sahne değişikliklerini Manuskript'te yap.

## Güvenlik
AI öneri verir; kanon kararı yazarda kalır. Kesinleşmemiş kararları Obsidian'a `Taslak`, `Belirsiz` veya `[BELİRLENMESİ GEREKİYOR]` etiketiyle ekle.
