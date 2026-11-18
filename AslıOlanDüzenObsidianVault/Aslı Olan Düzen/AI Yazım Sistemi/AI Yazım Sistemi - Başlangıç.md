# AI Yazım Sistemi - Başlangıç

Bu klasör, **Aslı Olan Düzen** romanını Manuskript sahneleri ile Obsidian kanon notlarını birleştirerek geliştirmek için kuruldu.

## Amaç
- Cebinden para çıkmadan çalışmak.
- Manuskript'teki sahneleri ve Obsidian vaultundaki roman bilgilerini aynı bağlamda kullanmak.
- Sadece fikir değil; ileriye dönük sonuçları, çelişki risklerini, karakter motivasyonlarını ve sahne uygulamasını da görmek.

## Kurulan yapı
- [[01 - Roman Fikir Motoru Promptu]]: Ana AI komutu.
- [[02 - Sahne İnceleme Şablonu]]: Yazılmış sahneyi denetleme şablonu.
- [[03 - Devam Fikri Şablonu]]: Bir sonraki sahne/bölüm için seçenek üretme şablonu.
- [[04 - Kanon Çelişki Kontrolü]]: Obsidian kanonuyla tutarlılık denetimi.
- [[Manuskript Obsidian Köprüsü]]: Manuskript dosyaları ile Obsidian notlarını nasıl birlikte kullanacağını anlatır.
- [[Güncel AI Bağlam Paketi]]: `ai_context_builder.py` betiğiyle otomatik üretilen birleşik bağlam dosyası.

## Ücretsiz çalışma prensibi
Bir AI aracı seçerken öncelik sırası:
1. **Hermes içinde dosya okutarak çalışma** — şu anda yaptığımız gibi, mevcut araçlarla vault ve sahne dosyaları okunur.
2. **Yerel model / Ollama** — bilgisayar kaldırırsa ücretsizdir, internet/API ücreti yoktur.
3. **Ücretsiz kota veren servisler** — sadece gerçekten ücretsiz kota varsa; ücretli API anahtarı/kredi kartı istememeli.

> Kural: Ücretli API, token başı ücret veya kredi kartı gerektiren servis bu sistemin varsayılan parçası değildir.

## Günlük kullanım
1. Manuskript'te sahneni yaz.
2. Şu betiği çalıştır: `C:/Users/alper/Desktop/Aslı Olan Düzen/ai_context_builder.py`
3. [[Güncel AI Bağlam Paketi]] güncellenir.
4. AI'ya şunu söyle:
   > [[Güncel AI Bağlam Paketi]] ve [[01 - Roman Fikir Motoru Promptu]] mantığıyla bu sahneyi/olayı analiz et.

## İstenecek çıktı formatı
AI'dan her zaman şu başlıklarla cevap iste:
- Kanonla uyum
- Çelişki riskleri
- Karakter motivasyonları
- 1985 evren uyumu
- Sebep-sonuç zinciri
- İleriye dönük sonuçlar
- Sahneye uygulanabilir somut öneriler
- Obsidian'da güncellenmesi gereken notlar
