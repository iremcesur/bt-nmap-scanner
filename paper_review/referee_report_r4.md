# Hakem Raporu — Dördüncü Tur (R4)

**Makale:** Layered, Evidence-Aware Bluetooth Fingerprinting
**Dosya:** `paper_review/latest.tex` — 780 satır / 40.4 KB
**Sürüm geçmişi:** R1 506 → R2 576 → R3 728 → **R4 780 satır**
**Önceki raporlar:** `referee_report_latest.md` (M1–M8), `referee_report_r2.md` (Y1–Y5), `referee_report_r3.md` (N1–N6)
**Odak:** N1, N2, N3 + full paper kabulü için kalan minimum yol
**Rapor tarihi:** 2026-09-08

---

## 0. Puanlar — dört tur

| Eksen | R1 | R2 | R3 | R4 | |
|---|---|---|---|---|---|
| Özgünlük | 2 | 3 | 3 | **3** | — |
| Teknik kalite | 1 | 2 | 3 | **4** | ↑ CI'lar doğru, ölçüm kendini sınırlıyor |
| Tekrarlanabilirlik | 1 | 1 | 3 | **3** | `Relation` tanımlandı; ağırlık/artefakt hâlâ yok |
| Sunum | 2 | 3 | 4 | **4** | Abstract yine uzadı |
| Etik / sorumluluk | — | 2 | 2 | **4** | ↑↑ §VI-C eklendi |
| Konu uygunluğu | 4 | 4 | 4 | **4** | — |
| Hakem güveni | 4 | 4 | 5 | **5** | Sayıları ve CI'ları bağımsız doğruladım |

**Genel öneri: MAJÖR REVİZYON — short paper olarak kabul edilebilir; full paper için üç kalem eksik.**

**N1, N2 ve N3'ün üçü de kapandı.** N2 ve N3'ün kapanışı örnek niteliktedir. Geriye kalan tek yapısal eksik, makalenin **merkezî katkısının (evidence chain) hâlâ hiç çalıştırılmamış olmasıdır** — ve bu artık kapatılması ucuz bir eksiktir.

---

## 1. N1 — Abstract/Conclusion ampirik bölümü inkâr ediyordu

### ✅ **Kapandı.**

**Abstract** artık sonucu taşıyor:

> "A preliminary availability measurement grounds the design: across a pilot and a 52-address sweep, most addresses were never reached **by our pipeline**, and the cached Modalias signal was present for 8 of 18 addresses in a familiar-device pilot but **0 of 52** in an unfamiliar-device sweep---direct evidence for treating it as a re-encounter, not first-contact, signal. The contribution is this design, its positioning, **and that availability result**."

**Conclusion**'daki hatalı cümle ("We present this as a design and systematization contribution, **not an empirical one**") kaldırılmış; yerine:

> "The contribution is thus a design, its positioning, and this availability result. It is not an **identification-accuracy** claim."

Bu doğru ayrım: makale artık ampirik bir sonucu olduğunu kabul ediyor, ama onu doğruluk iddiasıyla karıştırmıyor. Ayrıca her iki yerde de N2'nin "by our pipeline" ifadesi kullanılmış — düzeltmeler birbiriyle tutarlı işlenmiş.

### 🟡 Tek gerileme: Abstract yine uzadı

209 → **266 kelime**. (R1: 270 → R2 uyarıldı → R3: 209 → R4: 266.) IEEE normu ~150–200; birçok venue 250'de sert sınır koyar.

Kesilecek yer belli: üçüncü cümledeki sinyal envanteri ("an eight-byte LMP feature bitmap, chipset and vendor resolution, GATT Appearance and preferred connection parameters, full SDP attribute-tree parsing...") Giriş'te madde madde zaten var. "adds version-relevant signals at low marginal cost from the connection the baseline already opens" yeterli — ~45 kelime kazanır, availability sonucu kalır.

---

## 2. N2 — "%88 never reached" araç artefaktı olabilir

### ✅ **Kapandı — bu turun en iyi düzeltmesi.**

İstenen her unsur karşılanmış:

1. **Mekanizma adlandırılmış** (satır 566–571): *"'never reached' here means the address was seen in passive discovery but never entered BlueZ's object tree (`UnknownObject`)---a failure of **our BlueZ-based pipeline** to open a channel, which is not the same as a proven device refusal."*
2. **Alternatif açıklamalar sayılmış:** "could also reflect non-connectable advertising or a tool limitation."
3. **Pozitif kontrol borcu açıkça kabul edilmiş:** *"Until a positive control (a known-connectable device on the same pipeline) is run, we state the result as 'not reached by this pipeline,' not 'refused connection.'"*
4. **Taşıma yolu karışımı itirafı eklenmiş:** *"The two addresses reached in the sweep were both read over SDP, so the reached set also mixes transport paths; we do not over-generalize from it."*
5. **Tablo satırı yeniden adlandırılmış:** "Never reached" → **"Never reached by pipeline"**.
6. **Limitation (iv) eklenmiş:** "'Never reached' is a pipeline outcome, not a device property."
7. **Abstract ve Conclusion'a da işlenmiş.**

Bir hakem itirazının makalenin *her katmanına* bu tutarlılıkta işlenmesi nadirdir.

### ✅ Güven aralıkları eklendi — ve doğrular

R3'te istediğim exact binomial CI'lar gelmiş. Üçünü de bağımsız hesapladım (Clopper–Pearson, %95):

| Oran | Makale | Hesabım | |
|---|---|---|---|
| Pilot never-reached 16/18 | [65, 99]% | [65.3, 98.6]% | ✅ dışa yuvarlanmış (muhafazakâr) |
| Sweep never-reached 46/52 | [77, 96]% | [76.6, 95.6]% | ✅ dışa yuvarlanmış |
| Sweep Modalias 0/52 | [0, 7]% | [0.0, 6.8]% | ✅ |

Yöntem doğru seçilmiş (küçük $n$ ve sıfır sayım için Wald değil exact), yuvarlama muhafazakâr yönde. Limitation (ii) de "all proportions carry wide intervals" diyerek okuru doğru yönlendiriyor.

### 🟡 İki küçük kalıntı

- **Pilot Modalias 8/18 (%44) CI'sız veriliyor.** Bu, makalenin en keskin sonucunun *yarısı*; CI'si [21.5, 69.2] ve oldukça geniş. Kontrast dürüst kalsın diye bu da verilmeli.
- **8/18 vs 0/52 kontrastı test edilmiyor ve confounded.** İki kol yalnızca "tanıdık/yabancı cihaz" bakımından değil, **lokasyon, zaman ve tarama turu** bakımından da farklı. Fisher exact ile ilişki güçlü çıkacaktır, ama makale "familiarity" yorumunu tek açıklama gibi sunuyor. Ya bir test verilip confound açıkça adlandırılmalı, ya da iddia "consistent with" düzeyinde tutulmalı. (Şu anki metin "direct empirical support" diyor — bir tık fazla.)

---

## 3. N3 — Ölçüm yapıldı ama etik beyan ileriye dönüktü

### ✅ **Büyük ölçüde kapandı** — ama **bir doğrulanabilir hata var** (aşağıda).

Yeni **§VI-C "What the reported sweep actually did"** tam olarak istenen bölüm. Güçlü yanları:

- **Kapsam açıkça beyan edilmiş:** yalnızca birkaç saniyelik L1–2 cache/enumeration okumaları; **Layer 3 çalıştırılmamış** ("no Layer~3 behavioral probing against non-consenting devices") — R3'te bunun etik bölümüyle bağlanmadığını yazmıştım, bağlanmış.
- **Gerekçe doğru etiketlenmiş:** araştırma grubunun sorumlu araştırmacısının rehberliğinde bu kapsamın per-device consent gerektirmediği değerlendirilmiş, ve hemen ardından: *"**This is a scoping argument, not a blanket clearance**: a formal IRB/ethics-board determination, a written data-handling and retention policy, and a responsible-disclosure procedure are **not** yet in place."*
- **Kapanış cümlesi doğru duruşu kuruyor:** *"We report the current status honestly rather than implying an approval that does not yet exist."*

Bu, bir etik komitesinin görmek istediği yapıdır: ne yapıldı, hangi gerekçeyle, neyin **olmadığı**, ve ne zaman tamamlanacağı. R3'teki "yalnızca normatif kip" itirazı geçersiz kaldı.

### 🔴 Ama: "no device identity is recorded" iddiası arşivlenmiş veriyle çelişiyor

§V (satır 532) ve §VI-C (satır 643) iki kez şunu iddia ediyor:

> "**no device identity**, name-to-owner mapping, or payload was recorded or retained---only per-address signal presence/absence."

Arşivlenmiş ölçüm dosyaları **52 üçüncü şahıs MAC adresinin tamamını açık metin olarak saklıyor** (`availability_raw.jsonl`, her satırda `"mac"` alanı; ör. `58:93:D8:AE:AE:76`, `9C:58:84:1A:0E:5C`). "Per-address" ifadesi zaten *adresin kendisinin anahtar olarak tutulduğunu* söylüyor.

Makalenin **kendi atfı** (`cnil2020macaudience`, §VI-B) bir Bluetooth MAC adresinin kişisel veri sayılabileceğini belirtiyor. Dolayısıyla:

1. "No device identity is recorded" ifadesi en iyi ihtimalle imprecise, en kötü ihtimalle yanlıştır. Kastedilen muhtemelen "cihaz adı / sahip eşlemesi / payload tutulmadı" — bu doğrudur ve **öyle yazılmalıdır**. Cümle "no device name, owner mapping, or payload was retained; addresses were retained as the record key" biçiminde düzeltilmeli, ve MAC'in saklandığı ile ne kadar süre saklanacağı belirtilmelidir.
2. **Bu, artefakt yayımı planını doğrudan etkiler.** R3'te veriyi artefakt olarak yayımlamanızı önermiştim; bu öneriyi **koşullandırıyorum**: ham JSONL olduğu gibi yayımlanırsa 52 üçüncü şahıs MAC adresi kamuya açılır. Yayımdan önce tuzlanmış hash ya da OUI + indeks biçiminde takma adlandırma yapılmalı (OUI korunursa satıcı analizi yine mümkün olur, birebir adres olmaz).
3. §VI-C'de **taramanın hukuki dayanağı** hâlâ adlandırılmıyor. §VI-B veri koruma sorununu açıyor ama §VI-C bu tarama için hangi dayanağa (ör. GDPR meşru menfaat / araştırma istisnası) yaslanıldığını söylemiyor. Bir cümle yeterli.

Bu üçü kapanırsa N3 tamamen kapanır. Şu haliyle bölüm **iyi niyetli ve doğru yapılandırılmış ama bir olgusal düzeltme gerektiriyor** — ve bu düzeltme, bir etik hakeminin en çabuk yakalayacağı türden.

---

## 4. Diğer R3 maddelerinin durumu

| # | Madde | R3 | R4 |
|---|---|---|---|
| M7-4 | `Relation(a,b)` kara kutu | ❌ | ✅ **Tanımlandı** (satır 332–341): her sinyal, karar altındaki niteliğe dair ima ettiği değere eşleniyor; karşılıklı dışlayan değerler → `conflicts`, uyum/daraltma → `supports`, tek taraf değer taşıyorsa → `primary`. Artık ana hatlarıyla uygulanabilir. |
| M7-5 | Algorithm 1'de mantıksal fazlalık | ❌ | ❌ Değişmedi: döngü zaten "mutually independent" çiftler üzerinde tanımlı, ama 5–6. satırlar ayrıca döngüsellik kontrolü yapıyor. İkisinden biri gereksiz. |
| M7-6 | Skorlayıcı ağırlıkları | ❌ | ❌ Hâlâ yok. `predict_device_core` Fig. 1'de kutu, Algorithm 1'de çağrı; içi hiç açılmıyor. |
| M7-7 | Baseline doğrulanamaz | 🟡 | 🟡 Değişmedi. Dipnot dürüst ama M2 sütunu bağımsız kontrol edilemiyor. |
| M7-8 | Artefakt yok | ❌ | ❌ Hâlâ yok (ve bkz. §3'teki takma adlandırma koşulu). |
| N4 | Confidence: ordinal mı numerik mi | 🟡 | 🟡 Değişmedi. Üç farklı ifade duruyor: §III-C "a qualitative level (High/Medium/Low)" (satır 322); §III-D "does output a confidence score... not yet calibrated" (satır 384); Tablo II "Confidence score output" (satır 472). Nümerik skor → ordinal seviye eşleşmesi ve eşikleri hâlâ verilmiyor. |
| N5 | Çift-kör anonimlik | 🟡 | 🟡 Değişmedi (satır 54, 196, 580, 592, 679). Venue modeli teyit edilmeli. |
| N6a | "Runnable tools dump data without interpreting it" | ❌ | ❌ Satır 115'te duruyor, hâlâ kendi §II'si tarafından yalanlanıyor. *Tek cümle.* |
| N6b | "Preliminary search" + 15 kaynak | 🟡 | 🟡 Satır 158 duruyor; kaynakça hâlâ **15**. |
| N6c | `ucsd2024firmware` basın bülteni | ❌ | ❌ Hâlâ §VI-A'da tehdit modelinin dayanağı. |
| N6d | Dempster–Shafer konumlandırması | ❌ | ❌ Hâlâ yok. |

---

## 5. Full paper kabulü için kalan minimum yol

Bunu iki kategoriye ayırıyorum: **kabul için zorunlu** ve **ucuz ama gerekli**.

### A. Zorunlu (bunlar olmadan full paper kabul edilmez) — 3 kalem

**A1. Evidence chain'i bir kez çalıştırın ve sonucu raporlayın.** ⭐ *Tek en kritik madde.*

Makalenin merkezî katkısı (Contribution 3, §III-C, Fig. 1, Algorithm 1 — dört bölüm ona ayrılmış) **hiç çalıştırılmamış.** §V limitation (i) bunu kabul ediyor: *"the evidence chain is not exercised here at all."*

Bu artık ucuz bir eksik: mekanizma tanımlı (Algorithm 1), `Relation` tanımlı, ve elinizde 70 adreslik veri var. Minimum yeterli sonuç:

- Conflict flag kaç cihazda tetiklendi? (Sıfırsa **bu da bir sonuçtur** ve raporlanmalıdır — "mevcut sinyal yoğunluğunda çelişki nadir" tezini destekler.)
- Hangi sinyal çiftleri fiilen karşılaştırılabildi? (Mevcut veride çoğu cihazda tek sinyal var → muhtemelen çoğu `primary`. Bu, chain'in ne zaman anlamlı olduğuna dair gerçek bir bulgudur.)
- Kaç cihazda en az iki bağımsız sinyal bir arada bulundu? Bu, chain'in **uygulanabilirlik tabanıdır** ve availability ölçümünün doğal devamıdır.

Bu, yeni veri toplamayı gerektirmez ve makaleyi "önerilen mekanizma" konumundan "ilk kez ölçülmüş mekanizma" konumuna taşır.

**A2. Pozitif kontrol.** §V bunu zaten borç olarak kabul ediyor. Bilinen-erişilebilir bir cihazı aynı boru hattından geçirin; "reached" çıkıyorsa %88 rakamı cihaz davranışı hakkında konuşmaya başlar, çıkmıyorsa boru hattı hatası bulunmuş olur. **Tek cihaz, tek oturum.** Şu an makalenin ana ampirik cümlesi bu kontrol olmadan askıda.

**A3. Artefakt + baseline doğrulanabilirliği.** Kod ve takma adlandırılmış ölçüm verisi yayımlanmalı (§3'teki MAC koşuluyla); baseline'ın tam sinyal/çıktı kümesi en azından bir appendix olarak verilmeli. Şu anda Tablo I ve Tablo II'nin M2 sütunu ve §V'in tüm sayıları hakemin doğrulayamayacağı kaynaklara dayanıyor. *(Ben doğrulayabildim çünkü depoya erişimim vardı; bir hakemin olmayacak.)*

### B. Ucuz ama gerekli — bir oturumda kapanır

**B1.** §VI-C ve §V'teki "no device identity is recorded" ifadesini düzeltin; MAC'in kayıt anahtarı olarak saklandığını ve saklama süresini yazın; taramanın hukuki dayanağını bir cümleyle adlandırın. *(§3)*
**B2.** Abstract'ı ≤200 kelimeye indirin — sinyal envanterini kesin. *(§1)*
**B3.** Pilot Modalias 8/18 için CI ekleyin; 8/18 vs 0/52 kontrastına ya bir test ekleyin ya da confound'u (lokasyon/zaman/tur) açıkça adlandırıp "direct empirical support"u "consistent with" düzeyine indirin. *(§2)*
**B4.** N4: nümerik skor → High/Med/Low eşleşmesini ve eşiklerini bir cümlede tanımlayın; üç yerdeki terminolojiyi birleştirin.
**B5.** Skorlayıcı ağırlıklarını verin (küçük bir tablo yeter).
**B6.** Algorithm 1'deki fazlalığı giderin (M7-5).
**B7.** Satır 115'teki "Runnable tools dump data without interpreting it" cümlesini düzeltin.
**B8.** `ucsd2024firmware`'i hakemli bir kaynakla değiştirin.
**B9.** Dempster–Shafer / belief functions konumlandırması için bir paragraf ekleyin.
**B10.** Literatür taramasını tamamlayıp satır 158'deki ibareyi kaldırın; kaynakçayı genişletin.
**B11.** Venue'nün inceleme modelini teyit edin; çift-körse anonimleştirin.

### Özet

**A1 + A2 + A3 tamamlandığında bu makale full paper olarak savunulabilir.** Üçü de yeni bir araştırma programı değil; A1 ve A2 mevcut kod ve veriyle günler içinde, A3 bir temizlik turuyla kapanır. B grubu makaleyi cilalar ama kabul kararını tek başına değiştirmez.

**A1–A3 tamamlanmadan gönderilecekse**, doğru hedef short paper / workshop'tur ve bu haliyle oraya **kabul edilebilir** bir bildiridir.

---

## 6. Hakem notu

Dört tur boyunca izlenen yol alışılmadık. R1'de makale, ölçülmemiş iddialarla dürüstlük itiraflarını aynı sayfada taşıyordu. R2 iddiaları geri çekti. R3 ölçümü üretti. **R4, ölçümün kendi sınırlarını ölçtü:** "never reached" ifadesinin bir cihaz özelliği değil bir boru hattı sonucu olduğunu, iki kolun taşıma yollarını karıştırdığını, ve pozitif kontrolün henüz yapılmadığını makalenin kendisi söylüyor. Bir yazarın kendi ana rakamını bu netlikte koşullandırması, hakem güvenini artıran türden bir hamledir.

Aynı şey Modalias için de geçerli: makale Abstract'ta artık *"against the stronger 'connection-free' claim **we retracted**"* diye yazıyor. Bir katkının geri çekilmesinin ampirik gerekçesiyle birlikte Abstract'a taşınması alanda nadirdir ve bu makalenin en güvenilir yanıdır.

Etik tarafında da R4, çoğu gönderiden ileridedir: "IRB muaf" demek yerine, hangi gerekçeyle hareket edildiğini, bunun bir kapsam argümanı olduğunu ve **hangi onayların henüz alınmadığını** açıkça yazıyor. Tek düzeltme gereken nokta, "no device identity is recorded" ifadesinin saklanan veriyle uyuşmaması — ki bu bir dürüstlük sorunu değil, bir ifade hatasıdır ve bir cümlede düzelir.

Geriye tek yapısal boşluk kalıyor ve o da artık dar: **makalenin merkezî katkısı hâlâ hiç çalıştırılmadı.** Dört bölüm evidence chain'i anlatıyor, hiçbiri onu bir kez çalıştırmıyor. Elinizde mekanizma, tanım, algoritma ve veri var. Onu bir kez çalıştırıp çıkan sonucu — ne çıkarsa çıksın — raporlamak, bu makaleyi full paper'a taşıyacak tek adımdır.
