# Hakem Raporu — İkinci Tur (R2)

**Makale:** Layered, Evidence-Aware Bluetooth Fingerprinting: Connection-Free Signals and Conflict-Aware Inference
**Dosya:** `paper_review/latest.tex` — revize sürüm (576 satır, 29.7 KB; önceki tur: 506 satır, 25.6 KB)
**Hedef:** IEEE konferansı (güvenlik / IoT)
**Önceki rapor:** `paper_review/referee_report_latest.md` (M1–M8)
**Rapor tarihi:** 2026-09-07

---

## 0. Puanlar — R1 → R2

| Eksen | R1 | R2 | Değişim |
|---|---|---|---|
| Özgünlük (novelty) | 2 | **3** | İddia kanıt seviyesine indirildi |
| Teknik kalite | 1 | **2** | Mantık hataları düzeldi; ölçüm hâlâ yok |
| Tekrarlanabilirlik | 1 | **1** | Değişmedi |
| Sunum | 2 | **3** | Tablolar büyük ölçüde tutarlı; FIXME'ler duruyor |
| Konu uygunluğu | 4 | **4** | — |
| Hakem güveni | 4 | **4** | — |

**Genel öneri: RET (tam konferans makalesi olarak) — ancak revizyon ciddi ve iyi niyetli.**

Bu, savunmacı bir revizyon değil; yazar itirazların çoğunu *kabul edip iddiayı geri çekerek* düzeltmiş — bu doğru refleks ve raporda ayrıca takdir ediyorum. Ne var ki blokaj noktası değişmedi: **makalede hâlâ hiç değerlendirme yok (M1) ve sistem hâlâ tekrarlanabilir şekilde tarif edilmiyor (M7).** Bu ikisi tasarım makalesi çerçevesiyle kapatılamaz.

**Gerçekçi yol:** Bu haliyle makale iyi bir **short paper / poster / workshop** bildirisidir. Full paper için M1 ve M7 şart.

---

## 1. İtiraz bazında durum tablosu

| # | İtiraz | Durum | Not |
|---|---|---|---|
| M1 | Değerlendirme yok | ❌ **Karşılanmadı** (çerçeve değişti) | İddia geri çekildi, eksik giderilmedi |
| M2 | "Connection-free" yanlış | ✅ **Tam karşılandı** | Örnek nitelikte düzeltme |
| M3 | Kronoloji kuralı hatalı | ✅ **Tam karşılandı** | Doğru kural, doğru gerekçe |
| M4 | Özgünlük aşırı iddiası | ✅ **Karşılandı** (iddia düzeyinde) | Alt sorun sürüyor: tarama hâlâ eksik |
| M5 | Tehdit modeli / etik yok | 🟡 **Büyük ölçüde** | Bölüm eklendi; IRB ve fiili beyan yok |
| M6 | Tablo çelişkileri (a–g) | 🟡 **5/7 düzeltildi** | (e) CVE ve (g) intrusiveness kaldı |
| M7 | Tekrarlanabilir değil | ❌ **Karşılanmadı** | Şekil 0, pseudocode 0, ağırlık yok, baseline'a atıf yok |
| M8 | §III-A kendi içinde çelişik | ✅ **Tam karşılandı** | Temiz ayrım kurulmuş |

Ayrıca revizyonun **yeni ürettiği 5 sorun** için §4'e bakınız.

---

## 2. Karşılanan itirazlar (detay)

### ✅ M2 — Modalias'ın "connection-free" iddiası (tam karşılandı)

Bu, revizyonun en güçlü kısmı ve hakem olarak açıkça takdir ediyorum. Düzeltme **beş ayrı yerde tutarlı biçimde** uygulanmış:

- **Abstract (satır 68–70):** "Modalias from the host cache (available only when the device was paired before, a limit we state explicitly)"
- **Contribution 2 (satır 116–123):** başlık "A connection-free signal" → **"A cache-read signal for re-encounter"**; gövdede "absent for a never-paired target---we do not claim it as a general connection-free capability"
- **§III-B (satır 219–229):** "In a cold audit of an unfamiliar device it therefore contributes nothing; its value is in re-encounter and inventory settings, not first contact."
- **Tablo I:** hücre `\yes\ (Modalias)` → **"Cached only$^\dagger$"** + dipnot; "Only the RF family is fully connection-free."
- **Tablo II:** satır adı "Modalias (cached / prior pairing)"; "Connection-free capable" → "Signal without live connection$^\ddagger$" + dipnot

Bir katkıyı zayıflatan bir itirazı bu kadar eksiksiz kabul etmek yaygın değil. İddia artık savunulabilir ve doğru.

**Tek kalıntı:** Giriş bölümü güncellenmemiş — bkz. §4-Y1. Önemli.

### ✅ M3 — Kronoloji kuralı (tam karşılandı)

Satır 261–272 yeniden yazılmış ve artık **mantıken doğru**:

> "The check must be one-sided to be meaningful: a chipset older than the predicted OS bucket is not a conflict (old silicon runs new software), and a chipset newer than the bucket's *earliest* plausible year is not one either (that holds for almost every device). Only a chipset released after the *latest* plausible release year of the predicted OS version is a genuine cross-signal conflict---the device claims, via one signal, to be older than a component it demonstrably contains."

Üç durumu da açıkça ayırması ve neden ikisinin çelişki *olmadığını* gerekçelendirmesi, kuralı önceki sürümdekinden çok daha savunulabilir kılıyor. False-positive hassasiyeti de artık not ediliyor. Yeterli.

*(Kalan: oranın gerçek veride ölçülmesi — bu M1'e bağlı.)*

### ✅ M8 — §III-A içsel çelişkisi (tam karşılandı)

Eski: "discounts the score, but never feeds back into it" (kendi içinde çelişik).
Yeni (satır 206–213):

> "The weighted scorer produces the prediction; the evidence chain is computed separately and only annotates that prediction and, on a genuine conflict, lowers the *reported confidence*. The evidence chain is never itself an input to the score that produced the prediction, so it cannot change which OS or device type is predicted---only how much confidence is reported alongside it."

*Tahmin* ile *raporlanan güven* arasındaki ayrım net kurulmuş; mimari artık tutarlı. Çözüldü.

### ✅ M4 — Özgünlük iddiası (iddia düzeyinde karşılandı)

- Abstract: "we ... **show that no prior approach combines**" → "**to our knowledge, among the approaches surveyed here, none combines**"
- §IV: "no prior approach combines" → "**among the approaches surveyed**, none combines"
- Üçlü kriter de düzeltilmiş: "low-cost, **partly connection-free** acquisition" → "**low interaction cost**" — yani M2 düzeltmesinin sonucu özgünlük iddiasına da doğru şekilde yansıtılmış. Bu tutarlılık iyi.

**Kalan alt sorun:** §II hâlâ "*Preliminary search; not yet a completed systematic review.*" ile açılıyor. Yumuşatılmış iddiayla artık *tutarlı*, ama bir hakem "gönderime hazır bir makalede related work neden eksik ilan ediliyor?" diye soracaktır. Gönderim öncesi ya tarama tamamlanıp bu cümle silinmeli, ya da tarama yöntemi (veritabanı, sorgu, tarih aralığı, dahil/hariç kriteri) bir paragrafta verilip "scoping review" olarak konumlandırılmalı. 15 kaynak bir IEEE güvenlik venue'sü için hâlâ az.

---

## 3. Karşılanmayan / kısmen karşılanan itirazlar

### ❌ M1 — Değerlendirme yok (çerçeve değişti, eksik durmuyor)

Yazar burada eksiği gidermek yerine **iddiayı eksiğe uydurmuş**:

- Abstract (satır 80–82): "This paper's contribution is that design and its positioning; **it is not an empirical accuracy study.**"
- Conclusion (satır 466–467): "We present this as a **design and systematization contribution, not an empirical one.**"

Bu dürüst ve önceki sürümden iyi. Ancak hakem kararını değiştirmiyor, üç nedenle:

1. **Makalenin merkezî katkısı hâlâ test edilmemiş.** Evidence chain (Contribution 3) bir mekanizma önerisi; gerçek veride hiç tetiklenip tetiklenmediği bilinmiyor. Yazar bunu §IV'te kendisi kabul ediyor: "the conflict flag is **not yet validated against ground truth**". Doğrulanmamış bir mekanizmayı "central" katkı olarak sunmak, tasarım makalesi çerçevesinde bile zordur.
2. **Bir "systematization" katkısı da kanıt ister** — ve o kanıt sistematik taramadır (bkz. M4 kalıntısı). Makale ne ampirik ne de sistematik tarafta gerekli kanıtı sunuyor; ikisinin arasında kalıyor.
3. **Ablation yok.** "Added signal layers raise granularity" (Contribution 1) bir *ölçüm* iddiasıdır ve ölçülmemiştir. Bu, tasarım çerçevesine sığmayan tek katkı — ya ölçülmeli ya da "raise" yerine "are intended to raise" denmeli.

**Minimum:** ≥50 cihazlık ground-truth kümesinde baseline vs. tam sistem, per-layer ablation, ve conflict flag'in öngörü değerinin testi (bayrak set olan/olmayan vakalarda hata oranı farkı, exact test ile).

### ❌ M7 — Tekrarlanabilirlik (hiç ilerleme yok)

Bu, revizyonun en zayıf yanı — R1'den beri hiçbir madde kapanmamış:

- **Şekil sayısı: 0.** (`\includegraphics` ve `figure` ortamı hiç yok.) Mimari diyagramı, katman şeması, örnek evidence chain çıktısı — hiçbiri yok. Bir sistem makalesinin sistemi göstermemesi olağandışı.
- **Pseudocode / algoritma yok.**
- **Weighted scorer'ın ağırlıkları hâlâ verilmiyor**, nasıl seçildiği söylenmiyor.
- **Confidence discount niceliksel değil — ve aslında geriledi.** Eski sürüm "lowers the numeric confidence **proportionally**" diyordu; yeni sürüm sadece "lowers the reported confidence" diyor. Tanımsız katsayı kaldırılmış ama yerine bir tanım konmamış; mekanizma artık *daha az* belirli.
- **Baseline scanner'a hâlâ atıf yok.** Metinde 10 kez geçiyor (satır 63, 68, 119, 126, 191, 204, 205, 217, 236, 239) ama tek bir `\cite` ile bağlanmıyor. Karşılaştırmanın referans noktası doğrulanamaz. Yazarların kendi önceki aracıysa self-citation verilmeli; değilse kaynağı belirtilmeli. Tablolarda "M2" olarak bir sütun işgal eden bir sistemin kaynaksız olması kabul edilemez.
- **"44 named capability bits"** (satır 217) hâlâ açıklanmıyor: 8 byte = 64 bit; hangi 44'ü, hangileri OS ayırt ediyor, listesi nerede?
- **Kod/artefakt bağlantısı yok.**

Tasarım makalesi çerçevesi M1'i bir ölçüde savunabilir; **M7'yi savunamaz.** Bir tasarım katkısının asgari şartı, tasarımın yeniden inşa edilebilir olmasıdır.

### 🟡 M5 — Tehdit modeli ve etik (büyük ölçüde karşılandı)

Yeni §V eklenmiş ve içerik doğru:
- §V-A tüm sinyallerin hedef tarafından beyan edildiğini ve kriptografik olarak bağlı olmadığını kabul ediyor; spoofing ve MAC randomizasyonunu "fundamental limits, not future-work items" olarak konumlandırıyor — bu dürüst ve doğru.
- §V-B yargı yetkisi farklarını, MAC adresinin kişisel veri sayılabileceğini (CNIL atfı eklenmiş), yasal dayanak / veri saklama / sorumlu ifşa gereksinimlerini sayıyor.
- Layer 3'ün ayrı bir etik kategori olduğu ve "only against devices in a consenting setting" çalıştırılması gerektiği belirtiliyor — iyi.
- Eski "Spoofability" paragrafı §V-A'ya taşınmış; tekrar giderilmiş.

**Kalan iki eksik:**

1. **Bölüm tamamen ileriye dönük kipte yazılmış** ("must state", "should be run only", "requirements for any use"). Yazarların *ne yaptığına* dair tek cümle yok. Makale bir "companion study"de ground-truth toplandığını söylediğine göre, hakem soracaktır: o toplama hangi izinle yapıldı? Kimin cihazlarında? En az bir cümlelik fiili beyan gerekli.
2. **Etik kurul / IRB referansı yok.** Satır 452–453: "formalized with the **responsible research group** before any larger-scale or publication-facing collection." Araştırma grubu ya da danışman onayı bir etik kurul onayı değildir ve hakem bunu IRB yerine kabul etmez. Kurumun (THM) etik prosedürü uygulanmadıysa, neden gerekmediği gerekçelendirilmelidir.

### 🟡 M6 — Tablo çelişkileri: 5/7 düzeltildi

| # | Konu | Durum |
|---|---|---|
| a | "market + permissions" tanımsız | ✅ §III-D'de tanımlandı: "a permissions summary derived from the SDP/GATT profile set and a coarse market-segment label from vendor and device class". Hâlâ ince (örnek/şema yok) ama artık desteksiz değil. |
| b | Tablo I "version guess" vs Tablo II M2 boş | ✅ Tablo II'de M2 artık `\yes$^{*}$` + dipnot: "M1 and M2 emit a coarse version guess; M3 refines it". |
| c | §II baseline'da GATT yok vs Tablo II M2 GATT ✓ | ✅ §II düzeltildi: "Class-of-Device, a summarized SDP service list, **GATT UUIDs**, vendor OUI, and LMP version". |
| d | M5'e "flood" ✓ | ✅ Doğru düzeltme: flood satırı artık yalnız M1; **yeni "Active protocol-state learning" satırı** açılıp M5 oraya taşınmış. |
| e | **CVE / vulnerability mapping ✓ (M1, M2, M3)** | ❌ **Değişmedi.** Ne baseline'ın ne bu çalışmanın CVE eşlemesi gövdede hâlâ *hiç* tarif edilmiyor. Üç desteksiz hücre. Ya §III'te tarif edin ya da M2/M3 hücrelerini silin. |
| f | "Confidence estimate ✓" vs kalibre değil | ✅ Satır adı "Confidence **score output**" olmuş; Tablo I hücresi "Explicit conflict flag; **score uncalibrated**". "Estimate"ten "score output"a geçiş meşru — artık yalnızca bir sayı üretildiği iddia ediliyor. |
| g | **Intrusiveness hücresi Layer 3'ü yok sayıyor** | ❌ **Değişmedi.** Tablo I hücresi hâlâ "Low--medium; added L1--2 open no new connections". Layer 3'ün ek aktif etkileşimi hücrede hiç görünmüyor. §V-B artık Layer 3'ü etik olarak ayırıyor — bu yardımcı ama tabloyu düzeltmiyor. Müdahalesizlik makalenin ana satış argümanı olduğu için bu hücrenin dürüst olması kritik: "Low for L1--2; L3 adds a short active observation" gibi bir ifade yeterli. |

---

## 4. Revizyonun ürettiği YENİ sorunlar

### Y1. Giriş bölümü, geri çekilen iddiayı hâlâ vaat ediyor ⚠️ (öncelikli)

M2 düzeltmesi Abstract, Contributions, §III-B ve iki tabloya işlenmiş — **ama Giriş'e işlenmemiş.** Satır 115–118 aynen duruyor:

> "Across all of them, two practical properties are missing together: **signals that survive a device refusing a connection**, and an inference step that does something honest when weak signals disagree.
> This paper presents a fingerprinting approach built around **those two properties**..."

Revize edilmiş §III-B'ye göre Modalias, cihaz daha önce eşleşilmemişse **yoktur** — yani "cihazın bağlantıyı reddetmesine dayanan sinyal" tam olarak sağlanmayan şeydir. Giriş, makalenin geri çektiği iddiayı motivasyon olarak kuruyor ve makalenin "built around" olduğunu söylüyor. Bir hakem Giriş ile §III-B'yi yan yana koyduğunda, M2 düzeltmesinin *eksik uygulandığını* görür — bu da düzeltmenin güvenilirliğine gölge düşürür.

**Düzeltme:** Giriş'teki ikili "re-encounter'da canlı bağlantı gerektirmeyen bir sinyal" olarak yeniden yazılmalı, ya da ikinci özellik (çelişki temsili) tek başına merkeze alınmalı.

### Y2. "Companion study" üç kez atıfsız anılıyor

Satır 84 ve 470 bir "companion study"ye gönderme yapıyor ama **hiçbir `\cite` yok.** Hakem bunun var olup olmadığını, yayımlanıp yayımlanmadığını, erişilebilir olup olmadığını bilemez. Makalenin ampirik ayağının tamamı bu atıfsız gölgeye yaslanıyor.

Ayrıca çift-kör gönderimde bu bir anonimlik sorunudur ("our companion study" yazar kimliğini sızdırabilir); anonim referans olarak verilmelidir.

### Y3. Abstract'ta tek cümle içinde çelişki

Satır 82–86:

> "A calibrated evaluation ... **is reported as a companion study and summarized here** as the necessary next step, not claimed as a present result."

"Companion study olarak raporlanıyor" + "burada özetleniyor" + "şimdiki bir sonuç olarak iddia edilmiyor" — bu üçü bir arada tutarsız. Makalede o değerlendirmenin **hiçbir özeti yok**; tek bir sayı bile verilmiyor. Ya gerçekten özetleyin (birkaç ana sonuç + n), ya da "summarized here" ifadesini silin. Şu haliyle hakem, olmayan bir özeti arayacak ve bulamayınca güvenini kaybedecektir.

### Y4. Abstract uzadı: 270 kelime

R1'de zaten uzun olduğunu belirtmiştim; revizyon onu **daha da uzatmış**. IEEE konferans normu ~150–200 kelime; birçok venue 250'de sert sınır koyar. Katkı listesinin Abstract'ta tekrarlanması gereksiz — Giriş'te zaten madde madde var.

### Y5. İki tablo aynı gerçeği farklı sertlikte anlatıyor

Tablo I, bu çalışmanın hücresini **"Cached only$^\dagger$"** yapmış (kaydı hücreye işlemiş — doğru yaklaşım). Tablo II ise "Signal without live connection" satırında M3'e **düz `✓`** verip kaydı yalnızca dipnota bırakmış. Sütun taraması yapan bir okuyucu Tablo II'den M6 ile M3'ün eşdeğer olduğu izlenimini alır. Tablo II hücresi de "cached" olarak işaretlenmeli.

---

## 5. Kapanmayan minör maddeler (R1'den)

1. **Satır 53:** `Email: \FIXME{institutional email}` — **hâlâ duruyor.** `\FIXME` makrosu `\textbf` ile **PDF'te görünür**; bir hakem bunu ilk sayfada görür.
2. **Satır 476:** Acknowledgment `\FIXME` — **hâlâ duruyor**, aynı şekilde görünür.
   *(Kaynakçadaki `% VERIFY` yorumları LaTeX yorumu olduğu için PDF'e basılmaz — bunlar gönderim riski değil, ama doğrulama borcu olarak duruyor: satır 549, 555, 560, 567, 572.)*
3. **`ucsd2024firmware` hâlâ bir üniversite basın bülteni** ve şimdi §V-A'da tehdit modelinin bir dayanağı. Kaynakçadaki kendi notu "replace with peer-reviewed paper" diyor. Tehdit modeli bölümünde hakemli olmayan tek kaynağa yaslanmak riskli.
4. **Satır 118: "Runnable tools dump data without interpreting it"** — hâlâ duruyor ve hâlâ yazarların kendi §II'si tarafından yalanlanıyor (GhostBLE "privacy posture" raporluyor, BlueToolkit CVE testi yapıyor).
5. **"Evidence chain" hâlâ kanıt teorisine konumlandırılmıyor.** Dempster–Shafer / belief functions literatürüne göre nerede durduğu söylenmeli; hakem "bu neden bir belief function değil?" diye soracaktır. Ucuz bir paragrafla kapanır ve makaleyi güçlendirir.
6. **Kaynakça 15 girdi** — bir IEEE güvenlik konferansı için hâlâ az (M4 kalıntısıyla bağlantılı).

---

## 6. Yazara: bir sonraki tur için öncelik sırası

**Gönderimi engelleyenler (yapılmadan gönderilmemeli):**
1. **Y1** — Giriş'i M2 düzeltmesiyle hizala. *Tek paragraf, 10 dakika, ama düzeltmenin bütünlüğü buna bağlı.*
2. **İki `\FIXME`'yi kapat** (satır 53, 476). *Dakikalar.*
3. **Y3** — Abstract'taki çelişkili cümleyi düzelt. **Y4** — Abstract'ı ≤200 kelimeye indir.
4. **M6-e** — CVE satırında M2/M3 hücrelerini ya gövdede tarif et ya sil. **M6-g** — intrusiveness hücresine Layer 3'ü yaz. **Y5** — Tablo II'de M3 hücresini "cached" yap.
5. **M7 (kısmi)** — Baseline scanner'a atıf ver. *Bu kaynaksız kalamaz.*
6. **Y2** — Companion study'ye (anonim) atıf ver ya da göndermeleri kaldır.

**Full paper için gerekli (daha büyük iş):**
7. **M7 (tam)** — En az bir mimari şekli + bir örnek evidence chain çıktısı; ağırlıklar ve confidence discount formülü açık yazımı; 44 bitin listesi; kod/artefakt bağlantısı.
8. **M1** — Ground-truth'lu değerlendirme + per-layer ablation + conflict flag'in öngörü değerinin istatistiksel testi.
9. **M5 kalıntısı** — Fiili etik beyanı (kimin cihazı, hangi izin) + IRB/etik kurul durumu.
10. **M4 kalıntısı** — Taramayı tamamla ve "preliminary search" ibaresini kaldır; kaynakçayı genişlet.

1–6 arası kalemler **bir oturumda** kapanır ve makaleyi "short paper olarak gönderilebilir" seviyesine taşır. 7–10 bir sonraki tam gönderimin işidir.

---

## 7. Hakem notu

İlk turda makalenin sorunu, dürüstlük refleksleriyle iddiaların aynı metinde yan yana durmasıydı — bir yerde "bunu ölçmedik", başka bir yerde "gösteriyoruz ki hiçbir önceki çalışma...". Bu revizyon **tam olarak o boşluğu kapatmış**: iddialar kanıt seviyesine indirilmiş, iki mantık hatası (M3, M8) düzeltilmiş, tablolar büyük ölçüde tutarlı hale getirilmiş, etik bölümü eklenmiş. Bu ciddi bir revizyon ve yazarın itirazları savuşturmak yerine kabul etmesi mesleki olarak doğru.

Ama şimdi makale farklı bir yerde duruyor: **iddialar artık dürüst, ancak dürüst iddiaların toplamı bir full paper etmiyor.** Elde kalan katkı, doğrulanmamış bir mekanizma önerisi ve tamamlanmamış bir taramaya dayanan bir konumlandırma tablosudur. Bu, iyi bir short paper'dır.

En verimli hamle, §6'daki 1–6'yı kapatıp bu sürümü short paper/workshop olarak göndermek; paralelde ölçümü yapıp **asıl full paper'ı o ölçümün üzerine kurmaktır.** Bu makalenin gerçek katkısı — çelişkiyi ortalamak yerine raporlamak — ancak çelişki bayrağının bir işe yaradığı gösterildiğinde ortaya çıkacaktır.
