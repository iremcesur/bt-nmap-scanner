# Hakem Raporu — Üçüncü Tur (R3)

**Makale:** Layered, Evidence-Aware Bluetooth Fingerprinting
**Dosya:** `paper_review/latest.tex` — 728 satır / 37.0 KB
**Sürüm geçmişi:** R1 506 satır → R2 576 satır → **R3 728 satır**
**Önceki raporlar:** `referee_report_latest.md` (M1–M8), `referee_report_r2.md` (Y1–Y5)
**Odak:** M1 (availability ölçümü + Tablo III) ve M7 (Fig. 1, Algorithm 1, baseline atfı)
**Rapor tarihi:** 2026-09-08

---

## 0. Puanlar — R1 → R2 → R3

| Eksen | R1 | R2 | R3 | |
|---|---|---|---|---|
| Özgünlük | 2 | 3 | **3** | — |
| Teknik kalite | 1 | 2 | **3** | ↑ Ölçüm eklendi, doğrulanabilir |
| Tekrarlanabilirlik | 1 | 1 | **3** | ↑↑ Fig. 1 + Algorithm 1 + baseline dipnotu |
| Sunum | 2 | 3 | **4** | ↑ FIXME'ler kapandı, tablolar tutarlı |
| Konu uygunluğu | 4 | 4 | **4** | — |
| Hakem güveni | 4 | 4 | **5** | Sayıları arşiv veriyle doğruladım |

**Genel öneri: MAJÖR REVİZYON** (R1: Ret, R2: Ret).

Bu tur makaleyi kategori değiştirtti. Artık "kanıtsız bir tasarım bildirisi" değil; **doğrulanabilir bir ölçüm içeren, tekrarlanabilir şekilde tarif edilmiş bir tasarım makalesi.** Kalan itirazların hiçbiri temel değil — hepsi bir revizyon turunda kapanır.

**Kritik uyarı:** Aşağıdaki N1, makalenin *kendi en iyi sonucunu inkâr etmesi* sorunudur ve öncelikli olarak düzeltilmelidir.

---

## 1. M1 — Değerlendirme (odak değerlendirmesi)

### 🟢 Durum: **Kısmen karşılandı — ve karşılanan kısım örnek nitelikte**

Yeni §V ("Preliminary Signal-Availability Measurement") ve Tablo III eklenmiş. Kapsam dürüstçe sınırlandırılmış (satır 505–510):

> "This section measures one thing only: how often the added Layer~1--2 signals are actually *available*... It is *not* an identification-accuracy study... **Availability is the prior question: a signal that is rarely present cannot help however good the classifier is.**"

Bu çerçeveleme doğru ve savunulabilir. Üç nedenle bu, R2'deki "iddiayı geri çekme" hamlesinden niteliksel olarak farklı:

**(a) Turlar arası en ciddi metodolojik itiraz kapatılmış.** İlk analizde en ağır bulgu, `connectable` bayrağının döngüsel tanımlanmış olmasıydı: bağlanan ama sinyal yayınlamayan cihaz "bağlanamadı" hanesine yazılıyordu, bu da "ulaşılanlarda sinyal oranı"nı inşaen ~%100 yapıyordu. §V bunu açıkça düzeltmiş (satır 514–519):

> "Reachability is distinguished from signal richness explicitly: a device that opens a connection but exposes no tracked signal (``reached but quiet'') is counted as reached, not as a connection failure---**conflating the two would make ``fraction of reached devices exposing signal $X$'' partly circular.**"

Tablo III'te "reached but quiet" ayrı bir satır. Bu, itirazın hem tanınması hem de doğru çözülmesidir.

**(b) Sayılar arşiv veriden birebir yeniden üretiliyor.** Doğruladım:

| Tablo III hücresi | Kaynak veri | Sonuç |
|---|---|---|
| Pilot n=18: reached 2 | `availability_raw_pilot_cleaned.jsonl`, `connectable=true` → 2 | ✅ |
| Pilot: Modalias 8 | `modalias_present=true` → 8 | ✅ |
| Pilot: Appearance 1, SDP name 1 | → 1, 1 | ✅ |
| Sweep n=52: never reached 46 | 48 `device_unknown_to_bluez` − 2 connectable | ✅ |
| Sweep: reached 6 | 2 connectable + 4 `signal_not_present` | ✅ |
| Sweep: quiet 4 | `appearance_failure_category = signal_not_present` → 4 | ✅ |
| Sweep: Modalias 0, Appearance 0, SDP name 2 | → 0, 0, 2 (ikisi de "OBEX Object Push") | ✅ |

R1 turunda tablo rakamları arşiv veriyle uyuşmuyordu; **şimdi tamamen uyuşuyor.** Artefakt değerlendirmesinden geçer.

**(c) Ölçüm, makalenin kendi caveat'ını bağımsız olarak doğruluyor.** Modalias satırı (pilot 8/18 → sweep 0/52) R2'de metinsel bir kabul olan "Modalias yalnızca önceden eşleşilmiş cihazlarda vardır" iddiasının **ampirik kanıtı**. Bir yazarın kendi katkısını zayıflatan bir hipotezi test edip sonucu raporlaması nadirdir ve makalenin en güçlü tek sonucudur.

**Limitations alt bölümü de dürüst:** (iii) sinyal taşıyan iki pilot cihazından birinin araştırmacının kendi faresi olduğunu açıkça beyan ediyor; (iv) analiz sırasında bulunan bir araç hatasını (conn-params sorgusunun yanlış hata raporlaması) açıklıyor ve etkilenen hesaplamadan çıkarıldığını söylüyor. Bu düzeyde şeffaflık hakem güvenini artırır.

### Kalan eksikler (M1)

1. **Kimlik doğruluğu hâlâ ölçülmedi.** Makale bunu açıkça söylüyor ve kapsam dışı bırakıyor — kabul edilebilir, ama Contribution 1 ("added signal layers **raise output granularity**") hâlâ ölçülmemiş bir *ölçüm* iddiasıdır. Ya ablation ile desteklenmeli ya da "are intended to raise" denmelidir.
2. **Evidence chain hâlâ hiç test edilmedi.** §IV'te kabul ediliyor ("the conflict flag is not yet validated against ground truth"). Merkezî katkı olmaya devam ettiği için bu, full paper'a giden yolda tek gerçek engel. Basit bir ilk adım yeterli olurdu: mevcut 52 adreslik veride bayrak kaç kez tetikleniyor? Hiç tetiklenmiyorsa bu da raporlanabilir bir sonuçtur.
3. **Güven aralığı yok.** Tablo III artık sayı içerdiğine göre oranlar aralıksız verilemez: 6/52 = %11.5, exact binomial %95 CI ≈ [%4.3, %23.4]. Küçük $n$'de nokta tahmin yanıltıcıdır; CI eklemek makaleyi *güçlendirir*, zayıflatmaz.

---

## 2. M7 — Tekrarlanabilirlik (odak değerlendirmesi)

### 🟢 Durum: **Büyük ölçüde karşılandı**

| Alt madde | R2 | R3 |
|---|---|---|
| Mimari şekli | ❌ Yok | ✅ **Fig. 1** (satır 217–256), TikZ ile çizilmiş |
| Algoritma / pseudocode | ❌ Yok | ✅ **Algorithm 1** (satır 329–353) |
| Confidence discount tanımı | ❌ Tanımsız | ✅ **High → Med → Low, bir seviye** |
| Baseline'a atıf | ❌ Yok | 🟡 **Dipnot** (atıf değil) |
| "44 named capability bits" | ❌ Açıklanmamış | ✅ Açıklandı + örnekler |
| Ağırlıklar | ❌ Yok | ❌ Hâlâ yok |
| Kod / artefakt bağlantısı | ❌ Yok | ❌ Hâlâ yok |

**Fig. 1 iyi tasarlanmış.** Layer 0 → L1–2 / L3 ayrımını, ikisinin de skorlayıcıya aktığını, ve evidence chain'in **kesikli** okla yalnızca geri-anotasyon yaptığını gösteriyor. Kesikli ok seçimi M8'de düzeltilen ayrımı görsel olarak da doğru kodluyor: "never changing which type/OS is predicted". Metin ile şekil tutarlı.

**Algorithm 1, R2'deki en can sıkıcı belirsizliği kapatıyor.** R1'de "lowers confidence *proportionally*" (katsayı tanımsız), R2'de "lowers the reported confidence" (hiç nicelik yok) idi. R3 artık kesin: `LowerOneLevel: High → Med → Low`. §III-C bunu gerekçelendiriyor da (satır 316–319): *"a genuine conflict drops it one level rather than scaling a numeric probability, since the underlying weights are not yet calibrated."* Kalibre edilmemiş ağırlıklarla nicel bir olasılık ölçeklemek yerine ordinal bir düşüş seçmek **metodolojik olarak doğru karar** — ve gerekçesi yazılmış.

### Kalan eksikler (M7)

4. **`Relation(a,b)` bir kara kutu.** Algorithm 1 kontrol akışını formalize ediyor ama asıl çıkarımı yapan fonksiyon tanımsız. Makalede tek bir örnek var (chronology check); diğer sinyal çiftleri için "supports / conflicts / primary" nasıl belirleniyor? Bir okuyucu Algorithm 1'i uygulayamaz çünkü 7. satır tanımsız. **Bir tablo yeterli olurdu:** hangi sinyal çiftleri karşılaştırılıyor ve her biri için çelişki koşulu nedir.
5. **Algorithm 1'de mantıksal fazlalık.** Döngü zaten "each unordered pair of *mutually independent* signals" üzerinde tanımlı (satır 4), ama 5–6. satırlar ayrıca döngüsellik kontrolü yapıyor ("if $a$ was a scoring input for the branch $b$ tests → continue"). Bağımsızlık ön koşulu zaten sağlanıyorsa bu kontrol gereksizdir; sağlanmıyorsa döngü tanımı yanlıştır. İkisinden biri düzeltilmeli.
6. **Ağırlıklar hâlâ verilmiyor.** `predict_device_core` Fig. 1'de bir kutu, Algorithm 1'de bir çağrı; içi hiçbir yerde açılmıyor. Evidence chain iyi tarif edilmiş durumda, ama **tahmini üreten bileşen hâlâ tarif edilmemiş.**
7. **Baseline: atıf değil, dipnot.** Satır 191–195:
   > "A prior, unpublished active Bluetooth scanner developed within the same research project. We treat it as a given baseline and report only what the present work adds to it; its own design is not a contribution claimed here."

   Bu, R2'deki "hiç bahsedilmiyor" durumundan iyi ve kapsam sınırlaması dürüst. **Ama sorunu çözmüyor:** baseline yayımlanmamış ve erişilemez olduğu için Tablo I ve Tablo II'deki **M2 sütunu bağımsız olarak doğrulanamaz.** Hakem, karşılaştırmanın referans noktasını kontrol edemez. Asgari çözüm: baseline'ın tam sinyal/çıktı kümesini bir ek (appendix) olarak vermek, ya da kodu artefakt olarak yayımlamak.
8. **Kod/veri artefaktı yok.** Tablo III'ün sayıları arşiv veriden yeniden üretilebiliyor (ben yaptım), ama makale okuyucuya bu veriyi vermiyor. §V'in tamamı 70 satırlık bir JSONL ile doğrulanabilir hale gelirdi — artefakt yayımlamak buradaki en yüksek getirili tek hamle.

---

## 3. Diğer itirazların durumu

| # | İtiraz | R2 | R3 |
|---|---|---|---|
| M2 | "Connection-free" yanlış | ✅ | ✅ Ayrıca §V'te **ampirik olarak doğrulandı** |
| M3 | Kronoloji kuralı | ✅ | ✅ |
| M4 | Özgünlük iddiası | ✅ | 🟡 İddia doğru; §II hâlâ "Preliminary search" ilan ediyor (satır 153), kaynakça hâlâ 15 |
| M5 | Tehdit modeli / etik | 🟡 | 🟠 **Kötüleşti** — bkz. N3 |
| M6-e | CVE hücreleri desteksiz | ❌ | ✅ **Satır tamamen silinmiş** — doğru karar |
| M6-g | Intrusiveness'ta L3 yok | ❌ | ✅ "L1--2 add no new connections; **L3 adds a sustained active window**" |
| M8 | §III-A çelişkisi | ✅ | ✅ Fig. 1 ile görsel olarak da pekiştirildi |
| Y1 | Giriş geri çekilen iddiayı vaat ediyor | ❌ | ✅ "version-relevant signals gathered at low marginal interaction cost" |
| Y2 | Atıfsız "companion study" | ❌ | ✅ Kaldırıldı; yerine "the next submission" |
| Y3 | Abstract'ta çelişkili cümle | ❌ | ✅ Düzeltildi |
| Y4 | Abstract 270 kelime | ❌ | ✅ **209 kelime** |
| Y5 | İki tablo farklı sertlikte | ❌ | ✅ Tablo II satır adı "Modalias (cached; **prior pairing only**)$^\ddagger$" |
| — | İki görünür `\FIXME` | ❌ | ✅ **İkisi de kapandı**; Acknowledgment gerçek metin + görünmez `% TODO` |

R2'de açık kalan 13 kalemden 11'i kapanmış.

---

## 4. Bu turun YENİ bulguları

### 🔴 N1. Abstract ve Conclusion, makalenin kendi ampirik bölümünü inkâr ediyor (öncelikli)

Makale artık bir ölçüm bölümü ve Tablo III içeriyor. Buna rağmen:

- **Abstract (satır 80–82):** "The contribution is that design and its positioning; a calibrated accuracy evaluation on a ground-truthed corpus is left to future work, not claimed here." → §V'ten **tek kelime bahsetmiyor.**
- **Conclusion (satır 617):** "**We present this as a design and systematization contribution, not an empirical one.**" → Makalede bir empirik bölüm varken bu cümle *yanlıştır*.

R2'de bu cümleler doğruydu; R3'te içerik değişti, cümleler değişmedi. Sonuç iki yönlü zarar:

1. **Doğruluk:** Conclusion makalenin içeriğiyle çelişiyor. Hakem bunu "revizyon dikkatsizliği" olarak okur.
2. **Stratejik:** Makalenin **en savunulabilir sonucu** — Modalias'ın pilotta 8/18, sweep'te 0/52 çıkması — Abstract'ta da Conclusion'da da yok. Bu, kendi katkısını test edip doğrulayan bir sonuç ve makalenin en çok ilgi çekecek yeri. Şu anda §V'in içine gömülü.

**Düzeltme:** Abstract'a bir cümle ("A preliminary availability measurement over 70 addresses in two rounds shows reachability, not signal richness, is the binding constraint, and confirms the Modalias caveat empirically: present for 8/18 previously-paired pilot addresses and 0/52 in an unfamiliar-device sweep."), Conclusion'daki "not an empirical one" ifadesinin "the accuracy evaluation remains future work" ile değiştirilmesi. Katkı listesine beşinci madde olarak eklenmesi de düşünülmeli.

### 🔴 N2. "Never reached" bir cihaz davranışı mı, yoksa araç artefaktı mı?

Bu, §V'e yöneltilecek **en sert metodolojik itiraz** ve makale şu an cevaplamıyor.

Ham veride 52 adresin **48'i** `appearance_failure_category = device_unknown_to_bluez` taşıyor. Yani adres pasif keşifte görüldü ama BlueZ'in nesne ağacına hiç girmedi. Bu, "cihaz bağlantıyı **reddetti**" ile aynı şey değildir — keşif yolu ile sorgu yolu arasındaki devir teslimin başarısızlığı da olabilir.

Bunu güçlendiren bir gözlem: başarıyla ulaşılan 2 adres (`58:93:D8:AE:AE:76`, `9C:58:84:1A:0E:5C`) **de** `device_unknown_to_bluez` kategorisinde; ikisi de SDP üzerinden ("OBEX Object Push") okundu. Yani "reached" tanımı iki farklı taşıma yolunu (Classic/SDP ile BLE/GATT–D-Bus) karıştırıyor: bir cihaz bir yolda ulaşılamazken diğerinde ulaşılabilir sayılıyor.

Makalenin ana ampirik cümlesi (satır 550–552) buna dayanıyor:

> "reachability, not signal richness, is the binding constraint: 16 of 18 and 46 of 52 addresses were never reached at all"

Bu cümle, %88'lik oran bir araç/yol artefaktıysa çöker.

**Gerekli:** bilinen-erişilebilir bir kontrol cihazıyla pozitif kontrol (aynı boru hattından geçip "reached" çıkıyor mu?), ve `device_unknown_to_bluez`'in ne anlama geldiğinin açıkça tartışılması. Bu yapılana kadar bulgu "addresses were never reached **by this pipeline**" olarak ifade edilmelidir.

### 🟠 N3. Ölçüm yapıldı — ama etik bölümü hâlâ yalnızca ileriye dönük

R2'de §VI'yı "büyük ölçüde karşılandı" saymıştım; **R3'te bu değerlendirme geçersizleşti**, çünkü makale artık üç lokasyonda 52 üçüncü şahıs adresine aktif sorgu yaptığını *rapor ediyor*. Buna rağmen §VI hâlâ tamamen normatif kipte:

> "Any deployment or data collection built on this design **must state** (a) the legal basis and consent model..."

Yazarların kendi §V taraması için bu üç maddenin hiçbiri beyan edilmiyor. Hakem doğrudan soracaktır: *"Siz kendi (a), (b), (c)'nizi karşıladınız mı?"*

Olumlu tarafta §V bir gerçek önlem içeriyor: **"No device identity is recorded."** Bu iyi ve vurgulanmalı. Ama yeterli değil:

- Taramanın yasal dayanağı belirtilmemiş (Almanya/AB bağlamında BT MAC adresi kişisel veri sayılabilir — makalenin kendi CNIL atfı bunu söylüyor).
- Etik kurul / IRB durumu yok. Satır 601: "formalized with the **responsible research group**" — araştırma grubu onayı bir etik kurul onayı değildir.
- Layer 3'ün "only against devices in a consenting setting" çalıştırılması gerektiği söyleniyor; §V'te Layer 3'ün çalıştırılmadığı **açıkça belirtilmeli** (sadece L1–2 çalıştırıldığı satır 512'de yazıyor ama etik bölümüyle bağlanmamış).

**Gerekli:** §V'e veya §VI'ya iki-üç cümlelik fiili beyan — ne toplandı, ne toplanmadı (kimlik yok), hangi katmanlar çalıştırıldı, hangi izin/dayanakla, ve etik kurul gerekip gerekmediği ile gerekçesi.

### 🟡 N4. Confidence: ordinal mı, numerik mi?

Üç yerde üç farklı ifade:
- §III-C (satır 317): "the reported confidence, which is **a qualitative level (High / Medium / Low)**"
- §III-D (satır 370): "The scanner does output **a confidence score**, but it is not yet calibrated"
- Tablo II satırı: "**Confidence score output**"

Muhtemelen kastedilen: skorlayıcı nümerik bir skor üretir, raporlanan güven ondan türetilen ordinal bir seviyedir. Bu tutarlı bir tasarımdır — **ama makale bunu hiçbir yerde söylemiyor ve eşik değerlerini vermiyor.** Bir cümle ve eşikler yeterli.

### 🟡 N5. Çift-kör gönderimde anonimlik riski

Venue çift-kör ise üç sızıntı var:
- Satır 627 (Acknowledgment): "This work was carried out at the **CYSECDIGITAL research group, THM**." — gövde metninde kurum adı.
- Satır 191: baseline "developed within the **same research project**" — kendine gönderme.
- §V limitation (iii): "the **researcher's own** peripheral" — dürüst ama kimliklendirici.

Venue'nün inceleme modelini teyit edin; çift-körse Acknowledgment kör sürümde tamamen çıkarılmalı, diğer ikisi nötrleştirilmelidir. (Tek-kör/açık ise sorun yok.)

### 🟡 N6. Kalan minör kalemler

- **Satır 110:** "Runnable tools dump data without interpreting it" — R1'den beri duruyor ve hâlâ kendi §II'si tarafından yalanlanıyor (GhostBLE privacy posture raporluyor, BlueToolkit CVE testi yapıyor). Tek cümlelik düzeltme.
- **Satır 153:** "*Preliminary search; not yet a completed systematic review.*" — hâlâ duruyor, kaynakça hâlâ **15 girdi**. Gönderim öncesi ya tamamlanmalı ya tarama yöntemi bir paragrafta verilmeli.
- **`ucsd2024firmware`** hâlâ bir üniversite basın bülteni ve hâlâ §VI-A'da tehdit modelinin dayanağı. Kaynakçadaki kendi notu "replace with peer-reviewed paper" diyor.
- **Dempster–Shafer konumlandırması** hâlâ yok. "Evidence chain" terimi kanıt teorisi literatürüne bağlanmadan kullanılıyor; bir hakem "bu neden bir belief function değil?" diye soracaktır. Ucuz bir paragraf, ciddi kazanç.
- Kaynakçadaki 5 `% VERIFY` yorumu duruyor (PDF'e basılmaz, ama doğrulama borcu).

---

## 5. Bir sonraki tur için öncelik

**Kısa (bir oturumda kapanır, makaleyi gönderilebilir yapar):**
1. **N1** — Abstract ve Conclusion'ı §V ile hizala; availability sonucunu öne çıkar. *En yüksek getirili tek düzeltme.*
2. **N3** — §V/§VI'ya fiili etik beyanı + IRB durumu.
3. **N2 (metinsel kısmı)** — Bulguyu "never reached by this pipeline" olarak ifade et; `device_unknown_to_bluez`'i tartış.
4. **N4** — Numerik skor → ordinal seviye eşleşmesini bir cümleyle tanımla.
5. **M1-3** — Tablo III'e exact binomial CI ekle.
6. **N6** — Satır 110'u düzelt; `ucsd2024firmware`'i değiştir; Dempster–Shafer paragrafı ekle.
7. **N5** — Venue inceleme modelini teyit et.

**Orta (full paper için gerekli):**
8. **M7-4** — `Relation(a,b)` için sinyal-çifti/çelişki-koşulu tablosu. **M7-5** — Algorithm 1'deki fazlalığı gider.
9. **M7-6/8** — Skorlayıcı ağırlıklarını ver; kod ve `availability_raw*.jsonl`'i artefakt olarak yayımla. *§V'i tam doğrulanabilir yapar.*
10. **M7-7** — Baseline'ın sinyal/çıktı kümesini appendix olarak ver (M2 sütunu doğrulanabilsin).
11. **N2 (deneysel kısmı)** — Pozitif kontrol cihazıyla erişilebilirlik boru hattını doğrula.
12. **M1-2** — Evidence chain'i mevcut veride çalıştır; bayrak kaç kez tetikleniyor? Sıfırsa bile raporlanabilir.
13. **M4** — Taramayı tamamla, kaynakçayı genişlet.

---

## 6. Hakem notu

Üç turda makale gerçek bir yol katetti. R1'de sorun, dürüstlük itiraflarıyla desteksiz iddiaların aynı metinde yan yana durmasıydı. R2 iddiaları kanıt seviyesine indirdi ama ortada kanıt bırakmadı. **R3 kanıtı üretti** — ve bunu, kendi katkısını zayıflatma pahasına yaptı: Modalias ölçümü, yazarın kendi "connection-free" iddiasını geri çekmesinin ampirik gerekçesidir. Bir yazarın kendi aleyhine çıkan bir sonucu ölçüp raporlaması, bu turdaki en güçlü sinyaldir; §V'in limitations listesindeki kendi faresi ve kendi araç hatası itirafları da aynı yöndedir.

Aynı şekilde, R2'de yalnızca metinsel olan "evidence chain skoru değiştirmez" iddiası artık Fig. 1'de kesikli okla ve Algorithm 1'de ayrık dönüş değeriyle üç kez tutarlı biçimde kodlanmış durumda. Bu, tekrarlanabilirlik itirazına verilebilecek doğru cevaptı.

Kalan iş büyük ölçüde **muhasebe işi**: makale artık kendi içeriğinden daha az iddia ediyor (N1), yaptığı ölçümün etik beyanını vermiyor (N3), ve ana ampirik cümlesini araç artefaktı ihtimaline karşı henüz korumuyor (N2). Bunların hiçbiri yeni bir araştırma gerektirmiyor.

Şu anki haliyle bu makale **iyi bir short paper** ve M7'nin kalan maddeleri (özellikle artefakt yayımı ve `Relation` tablosu) kapatılırsa **savunulabilir bir full paper**dır. Evidence chain'in gerçek veride bir kez çalıştırılması — sonuç ne çıkarsa çıksın — makaleyi ampirik tarafa geçirecek son adımdır.
