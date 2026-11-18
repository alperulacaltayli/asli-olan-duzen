# GitHub Desktop — Windows kurulum ve kullanım

Bu proje için GitHub Desktop kullanarak klasörleri bilgisayarında düzenleyebilir, değişiklikleri tek tıklamayla GitHub'a gönderebilirsin.

## 1. Kurulum

1. Resmî indirme sayfasını aç: https://desktop.github.com/
2. Windows kurulum dosyasını indirip kur.
3. GitHub Desktop'ı aç.
4. **Sign in to GitHub.com** seçeneğiyle `alperulacaltayli` hesabına giriş yap.

## 2. Projeyi bilgisayara klonla

1. GitHub Desktop menüsünden **File → Clone Repository** seç.
2. **GitHub.com** sekmesinde `asli-olan-duzen` deposunu bul. Görünmüyorsa **URL** sekmesini seçip şu adresi gir:
   `https://github.com/alperulacaltayli/asli-olan-duzen.git`
3. Local Path alanında bilgisayarında kalıcı bir klasör seç. Örneğin:
   `C:\Users\KULLANICI_ADIN\Documents\GitHub\asli-olan-duzen`
4. **Clone** düğmesine bas.

## 3. Klasörleri düzenle

GitHub Desktop içinde **Repository → Show in Explorer** seçerek proje klasörünü aç.

Arşiv kayıtları `content\archives\` altında bulunur. Markdown dosyalarını Not Defteri, Visual Studio Code veya başka bir metin düzenleyiciyle açabilirsin.

Örnek: yeni bir kronoloji olayı eklemek için `content\archives\chronology\1938\` içine bir klasör aç, klasöre `index.md` koy ve olayını yaz. Alt olaylar için bu klasörün içine yeni klasörler ekle.

## 4. Değişiklikleri GitHub'a gönder

1. Dosyaları kaydet.
2. GitHub Desktop'a dön. Değişen dosyalar **Changes** sekmesinde görünür.
3. Sol alttaki Summary alanına kısa bir açıklama yaz. Örnek: `1938 kronolojisine yeni olay eklendi`.
4. **Commit to main** düğmesine bas.
5. Üstte görünen **Push origin** düğmesine bas.

Push işleminden sonra GitHub Actions arşiv klasörlerini tarar ve siteyi yeniden oluşturur. Başarılı Pages yayını tamamlandığında değişiklikler internet sitesine yansır.

## 5. Başka yerden değişiklik yaptıysan

Önce GitHub Desktop'ta **Fetch origin**, ardından gerekiyorsa **Pull origin** kullan. Böylece bilgisayarındaki kopya GitHub'daki en son sürümle eşitlenir.

## Önemli

- Projeyi sadece bir ana klasörde tut; aynı depoyu birden fazla farklı klasöre klonlama.
- Dosya eklerken `content/archives/` dışındaki teknik dosyaları gelişigüzel değiştirme.
- Yayımlanmamış roman bölümleri veya özel kanon notlarını açık depoya koyma.
- Her düzenlemeden önce değişen dosyaları kontrol et.
