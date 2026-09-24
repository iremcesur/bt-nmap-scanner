# Okuma Rehberi — kendi makaleni anlamak için

Bunu `latest.pdf`'in yanında açık tut. Amaç: makaleyi okurken "burada ne
demeye çalışıyorum ve doğru mu?" diye kontrol edebilmen. Teknik olmayan
dille yazıldı.

---

## BÖLÜM 1 — Makalen tek nefeste ne diyor?

"Bir Bluetooth cihazının işletim sistemini uzaktan tahmin etmeye çalışan
bir tarayıcı geliştirdim. Var olan bir tarayıcıya iki şey ekledim:
(1) az maliyetle daha çok sinyal okuyan katmanlar, (2) sinyaller
birbiriyle çelişince bunu tek bir skora ezmek yerine açıkça işaretleyen
bir 'kanıt zinciri'. Sonra bunu piyasadaki diğer yöntemlerle
karşılaştırdım ve gerçek dünyada ne kadar sinyal bulunabildiğini ölçtüm."

Önemli: Makale artık **doğruluk (accuracy) iddiası yapmıyor.** "Şu kadar
doğru tahmin ediyorum" demiyor. Onun yerine "hangi sinyaller ne sıklıkta
mevcut" ölçüyor. Bunu okurken aklında tut — çünkü çoğu düzeltme bu ayrımı
koruma üzerine.

---

## BÖLÜM 2 — Üç gerçek problem (sade dilde)

Danışmanın "submission'dan önce mutlaka" dediği üç şey. Kod veya veri
gerektiriyorlar, yani sadece yazıyla kapanmıyorlar.

### B1 — Skor tablosu bozuk (kod işi)
Android sürümünü tahmin ederken bir puan hesaplıyorsun, sonra bu puanı
sürümlere eşliyorsun. İki hata var:
- **Android 12 hiçbir zaman çıkamıyor.** Puanlar hep tam sayı, ama
  Android 12'nin denk geldiği aralıkta hiç tam sayı yok. Yani cihaz ne
  olursa olsun "Android 12" tahmini imkânsız.
- **1 puanlık küçük bir ekleme, tahmini iki sürüm birden atlatıyor**
  (75 → 76 puan = Android 11 → Android 13). Oysa makalen "bu küçük
  eklemeler tahmini değiştirmez" diye söz veriyor. Bu söz yanlış.
- Ayrıca eski bir hata: LMP 9 (Bluetooth 5.0) cihaz, LMP 10 (5.1)'den
  *daha yeni* bir Android'e eşleniyor — ters yönde.

Danışman diyor ki: bunları "gelecekte düzelteceğiz" diye duyurmak yetmez;
**kodu düzelt, sayıları yeniden hesapla, o paragrafı sil.** ("Açıklamak,
düzeltmenin yerine geçmez.")

### B2 — Kanıt zinciri hiç çalışmadı, ve sebebi anlaşılmamış (kod işi)
"Kanıt zinciri" makalenin en özgün fikri. Ama 43 gerçek taramada bir kez
bile tetiklenmemiş — hiç kayıt üretmemiş. Makale bunu "çelişki nadir"
diye açıklıyor. Danışman haklı olarak diyor ki bu açıklama yetmez:
mekanizma sadece çelişkileri değil, "destekliyor" kayıtlarını da eklemeli;
hiç kayıt olmaması bir **kod hatasına** işaret ediyor.

(Ben inceledim: makaledeki Algoritma 1, kodun gerçekte yaptığı şeyi
yansıtmıyor — ben idealize bir şey yazmışım, kod farklı çalışıyor. Bunu
düzelteceğiz.)

Danışman istiyor: 5 küçük test yaz (bir destekleyen çift, bir çelişen
çift, tek sinyal, atlanacak çift, boş girdi), mekanizmayı düzelt, arşivi
yeniden çalıştır.

### B3 — Etik/veri koruma sırası (veri/prosedür işi)
52 yabancı cihazın adresini aktif olarak sorguladın ve arşiv bu 52 MAC
adresini açık metin saklıyor. Sorun şu: kurumsal etik onayı toplama
*öncesinde* alınmalıydı, sonrasında değil. Bazı güvenlik konferansları
etik beyanı olmadan doğrudan reddediyor.

Danışman istiyor:
1. THM'nin **veri koruma sorumlusundan (DPO)** yazılı bir belge al (bu
   en kritik ve senin kontrolünde olmayan iş — **1. gün talep et**).
2. Arşivi **şimdi** takma-adlandır (biz aracı yazdık, çalıştırdık —
   `research/release/` altında hazır).
3. Bir saklama süresi belirt.
4. Yasal dayanağı **GDPR Madde 4(1)** yap (şu an dayandığın CNIL Fransız
   belgesi ikincil kalsın — sen Almanya'dasın).

**Bir de utandırıcı ama önemli sayı:** 70 adresin 62'sine hiç
ulaşılamadı. Yani çalışma büyük ölçüde yabancıların cihazlarına başarısız
bağlantı denemelerinden oluşuyor. Bu, "etik maliyet / veri getirisi"
oranının en kötü hali — hakemler bunu söyleyecek. Çözüm: yeni veri
toplamadan önce boru hattını (pipeline) düzeltmek.

---

## BÖLÜM 3 — Bölüm bölüm okuma rehberi

Her başlık için: **ne demeye çalışıyor** + **okurken neye dikkat et**.
"Dikkat et" notları danışmanın bulduğu çelişkilerle eşleşiyor; okurken
sen de göreceksin.

### Başlık (Title)
- Diyor: "Connection-Free Signals and Conflict-Aware Inference"
- Dikkat: "Connection-Free" iddiasını Bölüm V'te **geri çekiyorsun**.
  Yani başlık, gövdenin çürüttüğü bir şeyi iddia ediyor. → "Connection-
  Free" başlıktan çıkacak. (Danışman: T1)

### Abstract (özet)
- Diyor: ne yaptığını 200 kelimede özetliyor.
- Dikkat 1: "**replaces** the single fused score with an evidence chain"
  diyor. Ama gövde (Bölüm III-A) "zincir skoru **değiştirmez**, sadece
  üstüne not düşer" diyor. Abstract yanlış — doğrusu "supplements"
  (tamamlar), "replaces" (değiştirir) değil. (T5)
- Dikkat 2: "none combines..." (hiçbiri şunları birleştirmiyor) diyor ama
  Bölüm II "ön araştırma, tam sistematik tarama değil" diyor. Ön araştırma
  "hiçbiri" diyemez. Abstract da "taradıklarımız arasında" demeli. (T4)

### I. Introduction (giriş)
- Diyor: problem neden önemli, senin katkın ne.
- Dikkat: "out-of-date OS is a precondition for many attacks" cümlesi
  fazla güçlü — kaynak bunu bu kadar kesin söylemiyor, yumuşat. (§4)

### II. Background / Existing Approaches (ilgili çalışmalar)
- Diyor: diğer yöntemler (flooding, GATT, RF, araçlar) ve senin
  genişlettiğin "baseline" tarayıcı.
- Dikkat: Dipnottaki baseline "yayımlanmamış, katkımız değil" diyor — ama
  makaledeki her katkı ona göre "delta". Hakem göremediği bir şeye göre
  delta'yı değerlendiremez. (§5.7 — ya baseline'ı yayımla ya da "delta"
  çerçevesini bırak)

### III. Approach (yöntem) — makalenin kalbi
- **A. Overview + Şekil 1:** katmanların akışı. Dikkat: Şekil ve metin
  "weighted scorer" (ağırlıklı skorlayıcı) diyor, ama gerçekte sistem
  6 dallı bir **kural kaskadı**, sadece Android dalı sayısal. Aynı şeye
  iki farklı isim veriyorsun. (T6 — tek kelime kullan: "cascade")
- **B. Added signal layers:** LMP, Modalias, GATT, SDP.
  - Dikkat 1: "baseline'ın zaten açtığı bağlantıdan okunur" — **yanlış**.
    LMP/SDP = BR/EDR bağlantısı, GATT = LE bağlantısı; bunlar farklı
    bağlantılar. Her sinyalin hangi taşıma yolu olduğunu gösteren bir
    tablo gerekiyor. (Ben koddan doğruladım.)
  - Dikkat 2: Modalias'ın "önceki eşleşmeden gelir" dediğin populasyon
    mekanizması kodda kanıtlı değil — sadece BlueZ cache'inden okunuyor.
    Kesin mekanizmayı bilmeden iddia etme.
- **C. Evidence chain + Algoritma 1:** çelişki nasıl yüzeye çıkıyor.
  Dikkat: Algoritma 1 "her sinyal ÇİFTİ için" diyor ama tanım "her sinyal
  için" diyor, kod ise büsbütün farklı (sinyal-başına post-hoc denetim).
  Üçü birbirini tutmuyor. (B2 — kodun gerçekte yaptığıyla eşitleyeceğiz)
- **Scoring model + Tablo (ağırlıklar):** Android puanı. Dikkat: B1'deki
  iki bug burada. "105 tavan" diyorsun ama bonuslar toplamı 128'e
  çıkarabiliyor.
- **What is new:** baseline'a göre eklediklerin. Dikkat: "permissions"
  ve "market" çıktıları burada ilk kez geçiyor — daha önce hiç tanıtılıp
  doğrulanmamışlar. Ya tanıt ya listeden çıkar. (§4)

### IV. Comparison (karşılaştırma) — iki tablo
- Diyor: senin yaklaşımın diğerlerine göre hangi eksende nerede.
- Dikkat: Tablolar gövdeyle ve birbiriyle çelişmesin. Özellikle "OS +
  type + BT-era + market + permissions" çıktısı — BT nesli, cihaz yaşı ve
  OS sürümü üç ayrı şey; hangisini gerçekten üretiyorsun? Doğrulanmamışsa
  "OS version"ı çıktı olarak listeleme. (T7)

### V. Preliminary Signal-Availability Measurement (ölçüm) — asıl bulgu
- Diyor: gerçek dünyada ne kadar sinyal bulunabildi. "Ulaşılamadı /
  ulaşıldı ama sessiz / sinyal verdi" ayrımı ve güven aralıkları.
- Dikkat 1: "**Two rounds** were run" diyorsun ama başka yerde "what
  **five** rounds suggest" diyorsun. İki mi beş mi? Tek sayıya karar ver.
  (T2)
- Dikkat 2: "The **two** addresses reached" diyorsun ama tablo "6
  ulaşıldı" diyor. Kastettiğin "sinyal veren 2 adres" — öyle yaz. (T3)
- Dikkat 3: Kanıt zinciri "duman testi" olarak dürüstçe anlatıldı, iyi.
  Ama en güçlü fikir burada gömülü: **bağlayıcı kısıt sinyal kalitesi
  değil, sinyallerin bir arada bulunması.** Danışman bunu makalenin ana
  tezi yapmanı öneriyor (Structure A kararımız zaten bu yönde).

### VI. Threat Model & Ethics (tehdit modeli + etik)
- Diyor: cihaz her sinyalde yalan söyleyebilir; ve taramanın etik/hukuki
  çerçevesi.
- Dikkat 1: "cihaz her şeyde yalan söyleyebilir" = bu yöntem düşmanca bir
  hedefe karşı değil, sadece dürüst cihazlarda (envanter/denetim) anlamlı.
  Abstract'ın ilk cümlesi bunun tersini ima ediyor — düzeltilecek.
- Dikkat 2: "no device identity is recorded" derken arşiv 52 MAC saklıyor
  (düzelttik: "isim/sahip/payload saklanmadı, ama MAC saklandı"). B3.

### VII. Conclusion (sonuç)
- Dikkat: "signal availability, not classifier quality, is the first-order
  constraint" — ama sen iki nedeni karşılaştırmadın, sadece birini
  ölçtün. "bu boru hattıyla çoğu cihaza ulaşılamadı" diye ölçtüğün şeye
  indir. (§4)

### Referanslar
- Dikkat: [15] bir basın bülteni (UCSD haber sayfası) — gerçek hakemli
  makaleyle değiştir.

---

## Okurken not alman için 4 kural (danışmandan)

1. Hiçbir sayıyı uydurma/yuvarlama/tahmin etme. Yoksa `[EKSİK]` yaz, bırak.
2. Bir çelişkiyi, dürüst yarısını silerek çözme. Yanlış cümle değişir,
   doğru cümle kalır — asla tersi.
3. Sınırlılık (limitations) bölümlerini silme. Öz-eleştiri bir güç.
   Gidecek olan dürüstlük değil, dürüstlüğün anlattığı kusurlar.
4. Bölüm 2'deki her iddiayı okumadan önce, kaynağına güven — bunları ben
   koda karşı doğruladım.

---

## Okuduktan sonra

Bittiğinde bana "okudum" de. Sonra danışmanın Hafta-1 planındaki
**yazıyla kapatılabilir** düzeltmelere geçeriz (T1–T7 çelişkileri, transport
tablosu, Algoritma 1'i kodla eşitleme, stil pass). B1/B2 kod işi ve B3
DPO belgesi senin/danışmanın tarafında paralel yürür.
