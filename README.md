# OtoÇeviri

Klavyeyle yazdığın her şeyi, yazım tarzını bozmadan seçtiğin dile çevirir.

## Kurulum

```bash
pip install -r requirements.txt
```

## Çalıştırma

`baslat.bat` dosyasına çift tıkla. Saatin yanında **Ç** simgesi belirir.

- **Gri** simge: kapalı. **Yeşil** simge: açık.
- Simgeye **sol tık** ya da **Ctrl+Shift+Y**: Otomatik Çeviri'yi açar/kapatır (açılırken ince, kapanırken kalın bip sesi duyulur).
- Simgeye **sağ tık**: hedef dil, modlar, Windows açılışında başlatma, **Ayarlar…** ve çıkış.

## Kullanım

**Enter modu:** Türkçe yaz, Enter'a bas. Metin çevrilir ve gönderilir.
Discord, WhatsApp, Telegram, tarayıcıdaki sohbetler ve oyun içi sohbetler için uygundur.
- **Shift+Enter** her zaman normal çalışır (yeni satır).
- Komutlar (`/play ...`), linkler ve sadece emojiden oluşan mesajlar çevrilmez.
- Metin zaten hedef dildeyse dokunulmaz.
- Word, Excel, Not Defteri, VS Code, terminaller ve şifre yöneticilerinde Enter modu devreye girmez. Listeyi Ayarlar penceresinden düzenleyebilirsin.

**Kısayol modu (Ctrl+Shift+U):** Seçili metni çevirir ve yerine yazar. Seçim yoksa yazı kutusunun tamamını çevirir. Göndermez. Uzun metinlerde ve belgelerde bunu kullan.

Uygulamanın kısayolları diğer programlara iletilmez. Örneğin Discord'da Ctrl+Shift+U dosya seçme penceresini açmaz. Otomatik Çeviri kapalıyken Ctrl+Shift+U programın kendi işlevini görür. Ctrl+Shift+Y ise her zaman OtoÇeviri'ye aittir.

**Geri al (Ctrl+Shift+Z):** Kısayol modundaki son çeviriyi orijinal metne döndürür. Uygulama, çevrilmiş metni seçip gerçekten o çeviri olduğunu doğruladıktan sonra değiştirir. Arada metni düzenlediysen ya da başka yere tıkladıysan hiçbir şeye dokunmaz ve uyarır. Aynı pencerede ve 5 dakika içinde çalışır. Geri alınacak bir şey yoksa Ctrl+Shift+Z programın kendi işlevini görür (ör. yinele). Enter modunda gönderilen mesajlar geri alınamaz.

## Tarz koruma

Çeviri Google Translate ile yapılır, ardından yazış alışkanlıkların geri uygulanır:
- Hep küçük harfle yazıyorsan çeviri de küçük harf olur.
- BÜYÜK HARFLE yazdıysan çeviri de büyük harf olur.
- Sonuna nokta koymadıysan Google'ın eklediği nokta silinir.
- Emojiler ve satır boşlukları korunur.

## Ayarlar

Tepsi menüsünden **Ayarlar…** penceresini aç:
- Hedef dil, Enter modu, kısayol modu, açılışta aktif başlama
- **Windows açılışında başlat:** Kayıt defterinde yalnızca senin kullanıcı hesabına yazılır, yönetici izni gerekmez. Program (ya da ileride .exe) taşınırsa yol bir sonraki açılışta kendiliğinden düzelir.
- **Kısayollar:** "Değiştir"e bas, yeni tuş kombinasyonuna bas (Esc: iptal). Ctrl, Alt ya da Win tuşlarından biri olmalı.
- **Enter modunun çalışmayacağı programlar:** Her satıra bir program.

Değişiklikler Kaydet'e basınca hemen uygulanır, yeniden başlatmak gerekmez. Ayarlar `ayarlar.json` dosyasında saklanır.

## Bilinmesi gerekenler

- Çeviri sırasında pano kısa süreliğine kullanılır, işlem bitince eski metin geri konur. Panodaki resimler korunmaz.
- Yönetici olarak çalışan pencerelerde çalışması için uygulamayı da yönetici olarak başlatmak gerekir.
- Hile koruması olan bazı oyunlar sahte tuş basımlarını engelleyebilir.
- Yazdıkların hiçbir yere kaydedilmez. `otoceviri.log` dosyasına yalnızca hata mesajları yazılır.
- Hızlı deneme: `python ceviri.py en "naber kanka nasılsın"`
