# Hakem Raporu

**Makale:** Layered, Evidence-Aware Bluetooth Fingerprinting: Connection-Free Signals and Conflict-Aware Inference
**Dosya:** `paper_review/latest.tex` (506 satır, IEEEtran conference)
**Hedef:** IEEE konferansı (güvenlik / IoT)
**Rapor tarihi:** 2026-09-07

---

## 0. Puanlar

| Eksen | Puan (1–5) | Not |
|---|---|---|
| Özgünlük (novelty) | 2 | Fikir makul, ama "ilk/tek" iddiası kanıtlanmamış |
| Teknik kalite | 1 | **Hiçbir değerlendirme yok** — tek bir ölçüm, tablo satırı, sayı yok |
| Tekrarlanabilirlik | 1 | Kod yok, veri yok, algoritma/pseudocode yok, ağırlıklar yok |
| Sunum | 2 | Yazım akıcı; ama makalede FIXME'ler duruyor, hiç şekil yok |
| Konu uygunluğu | 4 | Venue için uygun bir problem |
| **Hakem güveni** | 4 | Alana hakimim; iddiaların çoğu makale içinden doğrulanabiliyor |

**Genel öneri: RET (Reject).**
Bu, düzeltilebilir bir sunum sorunu değil — makalede *değerlendirme bölümü yok*. Mevcut haliyle bir tasarım/pozisyon bildirisi; tam bir IEEE konferans makalesi değil. Aşağıdaki M1–M4 giderilmeden yeniden gönderim önerilmez. Kısa vadeli alternatif: workshop / short paper / poster olarak, iddiaları tasarım seviyesine indirerek.

---

## 1. Makalenin özeti (hakem okuması)

Yazarlar, mevcut bir aktif Bluetooth tarayıcısını iki yönde genişletiyor: (i) baseline'ın zaten açtığı bağlantıdan okunan ek sinyal katmanları (8-byte LMP feature bitmap, GATT Appearance ve preferred conn. params, tam SDP attribute tree) artı bağlantı gerektirmediği iddia edilen bir Modalias sinyali; (ii) tek bir füzyon skoru yerine, sinyalleri *supports / conflicts / primary* olarak etiketleyen ve çelişki halinde açık bir bayrak set eden bir "evidence chain". Katkı, dört eksende bir yetenek karşılaştırma tablosuyla konumlandırılıyor.

Problem gerçek ve motivasyon ikna edici. İtirazım fikre değil, **iddia ile kanıt arasındaki mesafeye**.

---

## 2. Güçlü yönler

1. **Problem seçimi yerinde.** Flooding tabanlı OS tespitine düşük-müdahaleli bir alternatif aramak meşru ve pratik bir ihtiyaç.
2. **Çelişkiyi ortalamak yerine raporlamak fikri doğru.** §III-C'deki "iki zayıf sinyal anlaşamadıysa bu bilgi korunmalı" argümanı, tek skorlu tarayıcılara karşı gerçek bir eleştiri ve denetçi için anlamlı bir çıktı.
3. **Döngüsellikten kaçınma bilinci var.** "Bir sinyal, beslediği toplam tahmine karşı kontrol edilmez" (§III-C) doğru bir metodolojik refleks — çoğu benzer araç bunu yapmıyor.
4. **Non-goals bölümü dürüst** (satır 138–142). Yazar neyi iddia etmediğini açıkça söylüyor; bu iyi.
5. Yazım temiz, cümleler net, IEEEtran kullanımı doğru.

---

## 3. Majör itirazlar

### M1. Makalede değerlendirme yok — ve bu, katkı iddiasını taşıyamayacak kadar merkezî bir eksik

Manuscript'in tamamında **tek bir ölçüm sonucu, tek bir sayı, tek bir doğruluk oranı, tek bir güven aralığı yoktur.** Abstract bunu kendisi itiraf ediyor (satır 80):

> "a calibrated accuracy evaluation on a shared corpus is identified as the next step"

Sorun şu ki makalenin merkezî katkısı olarak sunulan evidence chain (Contribution 3, satır 128–133), **doğru olup olmadığı hiç test edilmemiş bir mekanizmadır**. Sunulduğu haliyle şunları bilmiyoruz:

- Çelişki bayrağı gerçek veride kaç kez tetikleniyor? Hiç tetikleniyor mu?
- Tetiklendiğinde tahmin gerçekten daha mı sık yanlıştır? (Bayrağın *anlamlı* olması için gereken minimum kanıt budur.)
- Confidence discount uygulandığında sonuç iyileşiyor mu, kötüleşiyor mu?
- Eklenen katmanların her biri granülerliği ne kadar artırıyor? (Ablation yok.)

Bunlar olmadan Contribution 3 bir *öneri*dir, bir *sonuç* değil. Bir konferans makalesi öneriyle kabul edilmez.

**Ne gerekiyor:** ground-truth'lu bir cihaz kümesi (n ≥ 50, çeşitli üretici/OS), baseline vs. tam sistem karşılaştırması, katman katman ablation, ve conflict flag'in bir *öngörü değeri* olduğunun gösterilmesi (ör. bayrak set olan vakalarda hata oranı ile olmayanlarda hata oranı, exact test ile).

---

### M2. Merkezî "connection-free" katkısı, iddia edildiği anlamda connection-free olmayabilir

Satır 124–127:

> "The Modalias field is read from the host cache with **no live connection**, giving the method a usable signal even when a device refuses to connect---the single largest practical constraint on this class of tool."

BlueZ'in device property cache'i, **daha önceki bir eşleşme (pairing/bonding) oturumundan** doldurulur. Yazarların hedeflediği denetim senaryosunda hedef cihaz tanım gereği *daha önce eşleşilmemiş yabancı bir cihazdır* — bu koşulda cache boştur ve sinyal yoktur.

Yani sinyal "bağlantı gerektirmiyor" değil, "bağlantı geçmişte zaten kurulmuş olduğu için şimdi gerekmiyor". Bu ikisi bir denetim aracı için taban tabana zıttır. Katkı, ancak *hiç eşleşilmemiş* cihazlarda Modalias mevcudiyeti ölçülerek savunulabilir.

Bu itiraz makalenin dört katkısından ikisini (Contribution 2 ve Tablo I'deki tek `✓`) doğrudan etkiliyor.

**Ne gerekiyor:** eşleşmiş (bonded) ve hiç eşleşilmemiş cihaz kümelerinde Modalias mevcudiyet oranının ayrı ayrı raporlanması. İkinci küme için oran düşükse, katkı "connection-free signal" değil "bonded-device cache read" olarak yeniden çerçevelenmelidir.

---

### M3. Chronology conflict kuralı mantıksal olarak hatalı kurulmuş

Satır 241–244:

> "the release year of a Modalias-resolved chipset is checked against the OS-version bucket derived independently from LMP and profile flags; a chipset released **after that bucket's earliest plausible year** is a real cross-signal conflict, not a tautology."

Bu koşul çelişki üretmez. Bir OS sürümünün *en erken makul yılından sonra* çıkmış bir yonga tamamen normaldir — o OS'i çalıştıran her yeni cihaz bu koşulu sağlar. Örnek: Android 12 bucket'ı ≈2021 ise, 2023 çıkışlı bir yonga bu kurala göre "çelişki" sayılır, oysa Android 12 çalıştıran 2023 model bir telefon tamamen tutarlıdır.

Doğru çelişki koşulu ya "yonga, OS bucket'ının **en geç** mümkün tarihinden sonra" ya da "OS sürümü, yonganın çıkışından **önce**" olmalıydı.

Yazıldığı haliyle kural neredeyse her modern cihazda tetiklenir; bu da confidence discount'un neredeyse her vakada uygulanması demektir — yani ayırt edici gücü sıfırdır. Makalenin en somut çelişki örneği bu olduğu için, bu hata evidence chain'in inandırıcılığını doğrudan zedeliyor.

**Ne gerekiyor:** kuralın düzeltilmesi ve gerçek veride false-positive oranının raporlanması.

---

### M4. Özgünlük iddiası, makalenin kendi cümlesiyle çürütülüyor

Abstract (satır 76–79):

> "**we ... show that no prior approach combines** low-cost, partly connection-free acquisition, multi-OS granularity, and explicit conflict representation"

Related Work'ün ilk satırı (satır 148):

> "*Preliminary search; not yet a completed systematic review.*"

Bir "hiçbir önceki çalışma X'i birleştirmiyor" iddiası, tanım gereği kapsamlı ve sistematik bir literatür taraması gerektirir. Yazar aynı makalede bunu yapmadığını beyan ediyor. Bu iki cümle aynı PDF'te bulunamaz.

Ayrıca "show that" fiili karşılıksız: hiçbir şey *gösterilmiyor*, bir tablo dolduruluyor — ve o tablonun rakip sütunları birincil kaynaktan doğrulanmamış (kaynakçada satır 485, 490, 497, 502'de `VERIFY` yorumları hâlâ duruyor).

**Ne gerekiyor:** ya sistematik tarama yapılıp yöntemi raporlanmalı (arama motoru, sorgu dizisi, dahil/hariç kriterleri, tarih), ya da iddia "to the best of our knowledge, among the methods surveyed here" düzeyine indirilmelidir. Sadece 13 kaynakla mutlak bir kapsama iddiası savunulamaz.

---

### M5. Tehdit modeli ve etik bölümü yok

Makale, **üçüncü şahıslara ait cihazlara aktif olarak bağlanan ve sorgu yapan** bir sistem sunuyor (Layer 3 ayrıca 45 saniyelik ek gözlem yapıyor). Buna karşın manuscript'te:

- Tehdit modeli / saldırgan modeli tanımı **yok**
- Etik beyanı, IRB/etik kurul referansı, consent tartışması **yok**
- Yasal çerçeve (ör. Almanya/AB bağlamında radyo gözetimi) tartışması **yok**
- "Bu araç kötüye kullanılabilir mi" sorusuna dair tek satır **yok**

Bir güvenlik venue'sünde, kimliklendirme/parmak izi çıkarma yapan bir sistem için bu tek başına desk-reject gerekçesidir. Üstelik makale, ölçümün kimin cihazlarında, hangi izinle yapıldığını da söylemiyor (M1 nedeniyle zaten hiç ölçüm anlatılmıyor).

**Ne gerekiyor:** ayrı bir "Threat Model" ve "Ethical Considerations" bölümü; hangi cihazların hangi izinle tarandığı; pasif keşif ile aktif prob arasındaki hattın nerede çizildiği.

---

### M6. Tablolar makalenin gövdesiyle ve birbirleriyle çelişiyor

Tablolar makalenin *tek* kanıt aracı olduğu için (M1), içlerindeki her hücre eleştiriye açık. Aşağıdakiler doğrudan doğrulanabilir hatalar:

| # | Konum | Sorun |
|---|---|---|
| a | Tablo I, satır 292 | "This work" çıktı granülerliği: **"OS + type + BT-era + market + permissions"**. "market" ve "permissions" kelimeleri makalenin başka hiçbir yerinde geçmiyor. Tanımsız, desteklenmemiş çıktı iddiası. |
| b | Tablo I (satır 290) vs Tablo II (satır 331) | Tablo I baseline çıktısını "OS + type + **version guess**" diyor; Tablo II'de M2 için "OS version" satırı **boş**. Doğrudan çelişki. |
| c | §II (satır 184–188) vs Tablo II (satır 322) | §II baseline'ı "CoD, SDP flags, vendor OUI, LMP version" olarak tanımlıyor — GATT yok. Tablo II ise M2'ye "GATT services / characteristics ✓" veriyor. Çelişki. |
| d | Tablo II, satır 334 | "Behavioral response to flood" satırında **M5 (Pferscher, automata learning) ✓**. Automata learning bir flood değildir; aktif öğrenme sorgusu ile DoS-benzeri paket seli aynı şey değil. Rakip yöntemin yanlış karakterizasyonu. |
| e | Tablo II, satır 343 | "CVE / vulnerability mapping" M1, M2, M3 için ✓. Ne baseline'ın ne bu çalışmanın CVE eşlemesi gövdede **hiç tarif edilmiyor**. |
| f | Tablo II, satır 347 vs §III-D satır 266–267 | Tablo "Confidence estimate ✓" diyor; gövde "The scanner's confidence score is **not yet calibrated**" diyor. Kalibre edilmemiş bir skor bir "confidence estimate" olarak ✓ sayılamaz. |
| g | Tablo I, satır 292 | Intrusiveness "Low--medium; added L1--2 open no new connections". Layer 3'ün ek 45 s'lik aktif etkileşimi (§III-B) hücrede hiç yansıtılmamış — oysa müdahalesizlik makalenin ana satış argümanı. |

Bir hakem bu tablolardan birine güvenemezse, makalenin *tek* kanıt aracına güvenemez.

---

### M7. Sistem, tekrarlanabilir şekilde tarif edilmiyor

Makalede **hiç şekil yok** — mimari diyagramı, akış şeması, örnek çıktı, evidence chain örneği hiçbiri yok. Ayrıca:

- Weighted scorer'ın ağırlıkları verilmiyor, nasıl belirlendiği söylenmiyor
- "lowers the numeric confidence **proportionally**" (satır 246) — neye orantılı? Katsayı nedir? Tanımsız.
- Evidence chain kayıt formatı, karar kuralları, pseudocode yok
- "44 named capability bits" (satır 206) — 8 byte = 64 bit; 44'ünün hangileri olduğu, hangisinin OS ayırt ettiği söylenmiyor
- Kod/artefakt bağlantısı yok
- **"Baseline scanner" hiç atıf almıyor.** Yazarların kendi önceki aracıysa self-citation olarak verilmeli; değilse kaynağı belirtilmeli. Şu haliyle karşılaştırmanın referans noktası doğrulanamaz.

Bir okuyucu bu makaleden sistemi yeniden inşa edemez.

---

### M8. §III-A kendi içinde çelişiyor

Satır 199–202:

> "the evidence chain **annotates and, on a genuine conflict, discounts the score**, but **never feeds back into it**."

Skoru düşürmek (discount), tanımı gereği skora geri beslemedir. Ya evidence chain skordan bağımsızdır (ve o zaman discount yoktur), ya da skoru değiştirir (ve o zaman "never feeds back" yanlıştır). Bu, mimarinin en temel özelliğine dair bir belirsizlik ve düzeltilmesi zorunlu.

---

## 4. Minör itirazlar

1. **Satır 53:** `Email: [FIXME: institutional email]` — yazar bloğu eksik.
2. **Satır 406–407, 412:** Gövdede ve Acknowledgment'ta FIXME'ler duruyor. Bir hakem PDF'te FIXME görürse makalenin gönderime hazır olmadığını varsayar.
3. **`ucsd2024firmware` (satır 499–502)** bir **üniversite basın bülteni** ve gövdede iki kez (satır 174 ve 388) teknik bir iddiayı — "firmware güncellemesi RF parmak izini gizleyebilir" — desteklemek için kullanılıyor. Bu, RF ailesine karşı yöneltilen argümanın tek dayanağı. Hakemli kaynakla değiştirilmeli; yazarların kendi kaynakçası da bunu not ediyor.
4. **Satır 118–119:** "Runnable tools dump data without interpreting it" — aşırı genelleme, ve yazarların kendi Tablo I'i tarafından yalanlanıyor (GhostBLE bir "privacy posture" raporluyor, BlueToolkit CVE testi yapıyor; ikisi de yorum içeriyor).
5. **§III-B, Layer 3:** "we do not claim to have isolated yet" (satır 231) dürüst, ama o zaman bu katman Tablo II'de M3 için neden `✓`? Doğrulanmamış bir katman yetenek olarak sayılamaz.
6. **Related Work eksik.** "Preliminary search" itirafıyla tutarlı olarak, BLE reklam parmak izi, sniffer tabanlı pasif profilleme ve mobil OS telemetri ayrımı literatürü hiç yok. Kaynakça 14 girdi; bir IEEE güvenlik konferansı için tipik olarak az.
7. **Terminoloji:** "evidence chain" terimi kanıt teorisi (Dempster–Shafer, belief functions) ile ilişkilendirilmeden kullanılıyor. Hakem "bu neden bir belief function değil?" diye soracaktır — konumlandırma gerekiyor.
8. **Abstract çok uzun** ve katkı listesini tekrar ediyor; IEEE için ~150–200 kelimeye indirilmeli.

---

## 5. Yazarlara sorular

1. Hiç eşleşilmemiş (never-bonded) bir cihazda Modalias alanı ne sıklıkla dolu geliyor? Ölçtünüz mü?
2. `has_conflicting_signals` bayrağı, elinizdeki veride kaç kez tetiklendi? Tetiklendiği vakalarda tahmin doğruluğu ile tetiklenmediği vakalardaki doğruluk arasında fark var mı?
3. Confidence discount "proportional" ise, orantı katsayısı nedir ve nasıl seçildi?
4. Chronology kuralı için (M3): "earliest plausible year"dan *sonra* çıkan bir yonga neden çelişki sayılıyor? Bu kuralın false-positive oranı nedir?
5. Baseline scanner nedir, nerede yayımlandı/erişilebilir? Sizin önceki çalışmanız mı?
6. Tablo I'deki "market" ve "permissions" çıktıları nedir ve hangi sinyalden türetiliyor?
7. Layer 3'ün 45 s'lik gözlemi göz önüne alındığında, intrusiveness'ı "low--medium" olarak sınıflandırmayı nasıl gerekçelendiriyorsunuz?
8. Ölçümleriniz kimin cihazlarında, hangi izinle yapıldı? Etik onay alındı mı?

---

## 6. Kabul için gereken minimum yol

Bu makalenin bir sonraki gönderiminde **mutlaka** olması gerekenler:

1. **Bir değerlendirme bölümü.** Ground-truth'lu ≥50 cihaz, üretici/OS çeşitliliği raporlanmış, baseline vs. tam sistem, per-layer ablation, ve conflict flag'in öngörü değerinin istatistiksel testi. (M1)
2. **Modalias mevcudiyetinin bonded/never-bonded ayrımıyla ölçülmesi** — ya katkıyı doğrular ya da yeniden çerçevelenmesini gerektirir. (M2)
3. **Chronology kuralının düzeltilmesi** ve false-positive oranının verilmesi. (M3)
4. **Özgünlük iddiasının ya sistematik taramayla desteklenmesi ya da yumuşatılması.** (M4)
5. **Threat model + Ethical considerations bölümleri.** (M5)
6. **Her tablo hücresinin birincil kaynaktan doğrulanması**; gövdeyle çelişen hücrelerin düzeltilmesi; desteklenmeyenlerin silinmesi. (M6)
7. **En az bir mimari şekli, ağırlıkların ve discount formülünün açık yazımı, baseline'a atıf.** (M7)
8. Tüm FIXME'lerin ve `VERIFY` yorumlarının temizlenmesi.

Bunların 1–3'ü yapılmadan makale, hangi venue'ye gönderilirse gönderilsin aynı itirazla karşılaşacaktır.

---

## 7. Hakem notu

Bu makale kötü yazılmış değil — tam tersine, dürüstlük refleksleri iyi (non-goals bölümü, "not yet calibrated" itirafı, "preliminary search" notu). Sorun, o dürüstlüğün metinde **iddialarla yan yana** durması: makale bir yerde "bunu ölçmedik" derken başka bir yerde "gösteriyoruz ki hiçbir önceki çalışma..." diyor. Hakem bu iki cümleyi yan yana gördüğünde ikinciye güvenmeyi bırakır.

En verimli hamle, iddiaları eldeki kanıt seviyesine indirip **ölçümü yapmak** ve bir sonraki gönderimde asıl makaleyi o ölçüm üzerine kurmaktır.
