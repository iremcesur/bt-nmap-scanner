# Hakem Raporu — Beşinci Tur (R5)

**Makale:** Layered, Evidence-Aware Bluetooth Fingerprinting
**Dosya:** `paper_review/latest.tex` — 854 satır / 44.3 KB
**Sürüm geçmişi:** R1 506 → R2 576 → R3 728 → R4 780 → **R5 854 satır**
**Ek inceleme:** `research/pseudonymize_macs.py` (yeni)
**Odak:** Table I (skorlama ağırlıkları), Fig. 1, Algorithm 1, §V evidence-chain null sonucu, MAC takma adlandırma
**Rapor tarihi:** 2026-09-08

---

## 0. Puanlar — beş tur

| Eksen | R1 | R2 | R3 | R4 | R5 |
|---|---|---|---|---|---|
| Özgünlük | 2 | 3 | 3 | 3 | **3** |
| Teknik kalite | 1 | 2 | 3 | 4 | **4** |
| Tekrarlanabilirlik | 1 | 1 | 3 | 3 | **4** ↑ Table I + null sonucu |
| Sunum | 2 | 3 | 4 | 4 | **4** |
| Etik / sorumluluk | — | 2 | 2 | 4 | **5** ↑ Öz-düzeltme + araç |
| Konu uygunluğu | 4 | 4 | 4 | 4 | **4** |
| Hakem güveni | 4 | 4 | 5 | 5 | **5** |

**Genel öneri: MAJÖR REVİZYON — short paper olarak kabul; full paper için 4 somut kalem.**

R4'te "zorunlu" dediğim üç kalemden **A1 ve A3'ün araç tarafı** yapıldı, **A2 yapılmadı**. Buna karşılık Table I'in açılması **iki yeni, somut kusuru görünür kıldı** (§1) — bunlar dürüstlüğün değil, skorlayıcının sorunları ve full paper için düzeltilmesi gerekiyor.

---

## 1. Table I — Skorlama ağırlıkları (§III-E, yeni)

### ✅ Açıklama olarak: R4'ün B5 maddesi karşılandı, hem de beklenenden iyi

§III-E artık şunları veriyor: cihaz tipi için altı dallı, ilk-eşleşen-kazanır öncelik sırası; her dalın karar kuralı; yalnızca Android dalının nümerik olduğu; LMP sürümüne göre taban puanlar; profil bonusları; ölçekleme formülü $s' = (s/105)\times 10$; ve örnek eşikler. Ayrıca ağırlıkların statüsü doğru etiketlenmiş:

> "We report these values as the current engineering configuration, *not* as fitted or validated weights."

**Ve en dikkat çekicisi:** yazar kendi tablosundaki bir kusuru gizlemek yerine işaret ediyor:

> "the non-monotonic LMP rows (e.g. LMP~9 above LMP~10) are an un-calibrated artifact we flag rather than hide."

Bu, hakem güvenini artırır. Ama **işaret etmek düzeltmek değildir** ve full paper için yetmez.

### 🔴 T1. Non-monotonluk somut ve yön değiştiren bir hata üretiyor

Tablodaki taban puanları ve makalenin kendi ölçekleme/eşik formülünü uyguladım:

| LMP | BT sürümü | Taban | $s' = (s/105)\times10$ | Eşiğe göre çıktı |
|---|---|---|---|---|
| 9 | 5.0 | 85 | **8.10** | $\ge 7.0$ → **Android 11** |
| 10 | 5.1 | 68 | **6.48** | $\ge 4.0$ → **Android 10** |
| 11 | 5.2 | 85 | 8.10 | $\ge 7.0$ → Android 11 |

Yani **Bluetooth 5.1 bildiren bir cihaz, 5.0 bildiren bir cihazdan daha eski bir Android'e eşleniyor.** Bu bir kalibrasyon pürüzü değil; sistematik ve yönü belli bir hata: LMP 10 sınıfındaki her cihaz bir sürüm bucket'ı aşağı düşüyor. LMP 10 (BT 5.1) 2019 sonrası cihazlarda yaygın olduğu için etki de küçük değil.

**Gerekli:** ya satır düzeltilsin (LMP 10 ≥ 85), ya da tutuluyorsa hangi gözleme dayandığı yazılsın ve etkisi ölçülsün. "Flag rather than hide" bir short paper'da kabul edilebilir; full paper'da bilinen bir hatayı taşımanın gerekçesi olmaz.

### 🔴 T2. "max 105" tavanı bonuslarla aşılıyor — ölçekleme tanımsız kalıyor

Tablo başlığı "Android-branch score (**max 105**)" diyor ve ölçekleme 105'e bölüyor. Ama bonuslar taban puanın *üstüne* ekleniyor. En yüksek olası toplam:

```
LMP 14+ taban 105
+ A2DP/HFP/MAP/PBAP  4 × 2 = 8
+ OPP                      1
+ DID                      6
+ DID & LMP>=11            6
+ provisional LE/BR-EDR    1
+ provisional conn.int.    1
= 128   →   s' = 128/105 × 10 = 12.19
```

$s'$ 10'u aşıyor, yani ölçek tanım dışına çıkıyor. İki olasılık var ve makale hangisi olduğunu söylemiyor: (a) skor 105'te kırpılıyor — o zaman kırpma yazılmalı ve LMP 13–14 için bonusların çoğunun **etkisiz** olduğu belirtilmeli; (b) kırpılmıyor — o zaman "max 105" yanlış ve ölçekleme paydası hatalı. Tekrarlanabilirlik açısından bu boşluk doldurulmalı.

### 🟡 T3. Eşikler eksik veriliyor

Üç eşik "(e.g. ...)" ile örnek olarak veriliyor. Android 12/13/14 nereye düşüyor? Tam eşik listesi olmadan §III-E'nin geri kalanı uygulanabilir değil. Küçük bir tablo yeter.

### 🟡 T4. Dal öncelik sırası gerekçesiz

"First match wins" sırası (Apple → Android → IoT → PC → wearable → audio) bir tasarım kararı ve sonucu doğrudan etkiliyor, ama neden bu sıra olduğu söylenmiyor. Örneğin Apple dalı vendor'a bakıyor; Apple çipli bir Android aksesuarı ilk dalda yakalanır mı? Bir cümlelik gerekçe gerekli.

---

## 2. Fig. 1

### ✅ Yapı doğru ve metinle tutarlı

Katman ayrımı (L0 → L1–2 / L3), her ikisinin skorlayıcıya akışı ve evidence chain'in **kesikli** okla yalnızca geri-anotasyon yapması doğru kodlanmış. Başlık da bunu tekrarlıyor: "never changing which type/OS is predicted". M8'de düzeltilen ayrım artık metin, şekil ve algoritmada üç kez tutarlı.

### 🟡 F1. Şekil, §III-E'nin açtığı gerçekle artık çelişiyor

Fig. 1'in orta kutusu: `predict_device_core: **weighted score** → device type, OS, version`.

§III-E ise şunu söylüyor: cihaz tipi **kural tabanlı, öncelik sıralı bir dal kaskadı** ile belirleniyor; **yalnızca Android dalı** nümerik skor hesaplıyor; diğer beş dal sürümü kuralla atıyor. Yani "weighted score" kutusu sistemin çoğunluğunu yanlış temsil ediyor. Aynı yanlış etiket Algorithm 1'in 1. satırındaki `\Comment{weighted score}`'da da var.

**Düzeltme:** kutu "rule cascade (6 branches); numeric score on the Android branch" gibi bir şeye çevrilmeli. Bu, makalenin lehine bir düzeltme: kural kaskadı olduğunu söylemek, kalibre edilmemiş bir "ağırlıklı skor" iddiasından daha savunulabilir.

---

## 3. Algorithm 1

### ✅ İşlev olarak yeterli

`Relation` R4'te tanımlanmıştı; `LowerOneLevel` (High→Med→Low) tanımlı; dönüş değeri chain'i ve bayrağı ayrı taşıyor. Ana hatlarıyla uygulanabilir.

### 🟡 A-1. R3'ten beri açık olan mantıksal fazlalık hâlâ duruyor

Döngü zaten *"each unordered pair $(a,b)$ of **mutually independent** signals in $S$"* üzerinde tanımlı (satır 4). Hemen ardından 5–6. satırlar ayrıca döngüsellik kontrolü yapıyor ("if $a$ was a scoring input for the branch $b$ tests → continue"). Bağımsızlık ön koşulu zaten sağlanıyorsa bu kontrol ölü koddur; sağlanmıyorsa döngünün "mutually independent" nitelemesi yanlıştır. **Üçüncü turdur açık.** İkisinden biri seçilmeli — muhtemelen doğrusu: döngüyü tüm çiftler üzerinde tanımlayıp bağımsızlık testini gövdeye almak.

### 🟡 A-2. Karmaşıklık ve `primary` semantiği

Döngü tüm çiftler üzerinde $O(|S|^2)$; küçük $S$ için sorun değil ama belirtilmesi iyi olur. Daha önemlisi: `Relation` tanımına göre `primary`, "yalnızca birinin değer taşıması" durumu. Bu durumda bu bir *çift* ilişkisi değil, tek sinyalin niteliğidir — ve aynı sinyal $|S|-1$ çiftte tekrar tekrar `primary` olarak zincire yazılır. §V'in "the evidence chain was empty for every scan" bulgusuyla birlikte okununca, `primary` kayıtlarının niçin hiç üretilmediği de belirsizleşiyor. Semantik netleştirilmeli.

---

## 4. §V — Evidence-chain null sonucu ⭐

### ✅ R4'ün A1 maddesi yapıldı — ve dürüstçe raporlandı

Yeni "Evidence-chain firing (preliminary)" paragrafı: 8 farklı cihazı kapsayan 43 tam tarama arşivi üzerinde çıkarım adımı çalıştırılmış; `has_conflicting_signals` her taramada false, zincir her taramada boş. Sonuç saklanmamış, aksine iki açıklama önerilmiş ve şu cümleyle çerçevelenmiş:

> "This is a reportable null result, not a demonstration that the mechanism works."

Bu, R4'te istediğim adımdır ve doğru yapılmıştır.

### 🔴 V1. Ama bu bir "null result" değil — geçersiz bir test

Makalenin kendi ikinci açıklaması testi geçersiz kılıyor:

> "the numeric `confidence_score` field is populated in only **1 of the 43** records, indicating **most of this archive predates the current evidence-chain build**."

Yani 43 kaydın 42'si, test edilen zincir yapısından **önceki** bir sürüm tarafından üretilmiş. Güncel çıkarım adımı bayat girdiler üzerinde çalıştırılmış. Bu durumda "hiç tetiklenmedi" bulgusu mekanizma hakkında bilgi taşımıyor.

Terminoloji önemli: **null result**, geçerli bir testin etki bulamaması demektir ve raporlanabilir. Buradaki durum bir *implementation smoke test* — uçtan uca çalıştığının gösterimi, mekanizmanın sınanması değil. Makale "not yet meaningfully exercised" diyerek doğru yöne gidiyor ama "reportable null result" ifadesi hâlâ olduğundan fazlasını ima ediyor.

**Düzeltme:** "We executed the chain end-to-end (an implementation check); the archive cannot exercise it, since 42 of 43 records predate the current build." Bu, daha zayıf ama doğru bir ifadedir ve hakem itirazını peşinen kapatır.

### 🔴 V2. Yorumlanabilirlik için gereken tek sayı eksik

"Hiç tetiklenmedi" ifadesi, **paydası olmadan** okunamaz. Eksik olan sayı şu: *43 taramanın kaçında en az iki bağımsız sinyal aynı anda mevcuttu?* Çünkü bu, çelişkinin ön koşuludur ve makalenin kendi açıklaması da buna dayanıyor ("a second *independent* signal---the precondition for any conflict---was rarely present").

- Eğer cevap 0 ise: tetiklenmeme **matematiksel olarak zorunludur** ve rapor edilecek bir "sonuç" yoktur; mekanizmanın uygulanabilirlik tabanının sıfır olduğu vardır — ki bu başlı başına önemli bir bulgudur.
- Eğer cevap örneğin 12 ise: 0/12 tetiklenme gerçek ve anlamlı bir gözlemdir.

Bu sayı aynı arşivden hesaplanabilir ve **null sonucu yorumlanabilir kılan tek veridir.** Eklenmesi zorunlu.

### 🟡 V3. İki veri kümesinin neden farklı olduğu açıklanmıyor

§V'in availability ölçümü 70 adres (18+52) üzerinde; zincir çalıştırması **farklı** bir arşiv üzerinde (43 tarama / 8 cihaz). Neden sweep verisi kullanılmadı? Muhtemel cevap doğru ve savunulabilir: sweep yalnızca L1–2 availability sorgularını çalıştırdı, tam tahmin üretmedi — dolayısıyla zinciri besleyemez. Ama makale bunu söylemiyor ve hakem "neden kendi ölçtüğünüz veriyle test etmediniz?" diye soracaktır. Tek cümle.

### 🟡 V4. Örneklem bağımsız değil

"8 distinct devices, **largely the authors' own**". Bu, incelemenin ilk turundan beri süregelen kendi-cihaz kontaminasyonu sorunudur. Kabul edilmiş olması iyi; ama sonucun taşıyabileceği ağırlığı belirliyor ve V1 ile birleşince zincir hakkında hiçbir çıkarım kalmıyor. *(Ayrıca "the authors'" çoğul ifadesi makalenin diğer yerlerindeki "the researcher's" tekil ifadesiyle uyuşmuyor — tek yazarlı bir makalede tutarlılık gerekir, ve çift-körse ayrı bir sorun.)*

### 💡 V5. Bu bulgu makalenin en ilginç yeri — ve gömülü duruyor

Availability sonucu ile zincir bulgusu birleştiğinde ortaya tutarlı ve özgün bir tez çıkıyor:

> Bu sınıf araçlarda bağlayıcı kısıt sinyal *kalitesi* değil, sinyal **eş-mevcudiyeti**dir: cihazların çoğuna hiç ulaşılamıyor; ulaşılanların çoğu tek bir sinyal veriyor; ve çelişki temelli çıkarım **iki bağımsız sinyalin aynı anda bulunmasını** gerektirdiği için pratikte nadiren uygulanabiliyor.

Bu, "önerdiğimiz mekanizma iyidir" iddiasından daha ilginç ve daha savunulabilir bir katkıdır — ve makalenin kendi verisiyle destekleniyor. Şu anda §V'in son paragrafına gömülü. V2'deki sayı eklenirse bu tez ölçülmüş hale gelir ve makalenin ana hikâyesi olabilir.

---

## 5. MAC takma adlandırma

### ✅ Makale tarafı: R4'ün B1 maddesi tam karşılandı — örnek nitelikte öz-düzeltme

§VI-C artık şunu yazıyor:

> "no device name, name-to-owner mapping, or payload was recorded or retained---only per-address signal presence/absence **and the raw MAC**. We are precise here because **an earlier phrasing (``no device identity is recorded'') was inaccurate**: the raw JSONL archive stores each third-party MAC in cleartext, and a MAC can itself be personal data. Before any artifact release the archive **must be pseudonymized**..."

Bir makalenin önceki bir ifadesinin yanlış olduğunu açıkça yazıp düzeltmesi nadirdir. Etik bölümü artık bu makalenin en güçlü yanlarından biri.

### ✅ Araç tarafı: `pseudonymize_macs.py` doğru primitifleri kullanıyor

- **HMAC-SHA256 + 32 baytlık rastgele tuz** (`secrets.token_bytes`). Bu kritik: çıplak SHA256(MAC) kırılabilirdir — MAC uzayı ~2⁴⁸ ve OUI bilinince çok daha küçük; kaba kuvvetle tersine çevrilir. Tuzlu HMAC doğru seçim.
- Tuz dosyası `chmod 0600`, "keep private; do NOT release" uyarısı, ve sonda ikinci bir hatırlatma.
- Aynı tuzla eşleme kararlı → bir cihaz iki turda aynı takma adı korur (uzunlamasına analiz mümkün kalır).
- Girdiyi yerinde ezmeyi reddediyor; `mac` dışındaki alanlar aynen geçiyor; kayıtlara `mac_pseudonymized` işareti konuyor.
- 10 hex (40 bit) kırpma: $n{=}52$ için çarpışma riski ihmal edilebilir, sorun değil.

### 🔴 P1. Araç henüz çalıştırılmamış — ortada takma adlandırılmış artefakt yok

`research/` altında bir çıktı dosyası yok; ham `availability_raw.jsonl` hâlâ 52 açık MAC taşıyor. Makale takma adlandırmayı "release prerequisite" ilan ediyor — doğru — ama full paper artefakt talebini karşılamak için **dosyanın üretilip yayımlanması** gerekiyor. Şu anki durum: "araç hazır, iş yapılmadı."

### 🔴 P2. Yalnızca `mac` dönüştürülüyor; arşivdeki diğer yeniden-tanımlama vektörleri duruyor

Script'in docstring'i arşivi "yayımlanabilir" kılmaktan söz ediyor, ama sadece `mac` alanına dokunuyor. Arşivde ayrıca şunlar var:

- `timestamp` — **saniye çözünürlüğünde** (ör. `2026-08-31T19:00:17`)
- `modalias_raw`, `modalias_vendor_resolved` (pilotta gerçek satıcı adları: Google, Samsung, Apple)
- `gatt_appearance_raw`, `sdp_records_raw`, `sdp_service_name`

Makale taramanın **üç lokasyonda** yapıldığını söylüyor. Saniye çözünürlüklü zaman damgası + satıcı + sinyal profili, o lokasyonlarda bulunmuş biri için 52 satırlık bir kümede yeniden tanımlamaya yeter. **Öneri:** zaman damgalarını tur kimliğine ya da tarihe indirgeyin; `*_raw` alanlarını yayım öncesi gözden geçirin; script'in docstring'i neyi kapsamadığını açıkça söylesin.

### 🟠 P3. `--scheme oui-index` fazla iyimser tanıtılıyor

Docstring: *"This preserves vendor-level analysis while removing the unique identifier."* OUI korunup zaman damgası ve satıcı dizesi de kaldığında "unique identifier kaldırıldı" ifadesi fazla güçlü. Bu şema yayım varsayılanı olmamalı; kullanılacaksa P2'deki indirgemelerle birlikte kullanılmalı.

### 🟡 P4. İki operasyonel pürüz

- **Tuz dosyasının varsayılan yolu `OUT.jsonl.salt`** — çıktının hemen yanında. Bir dizin arşivlenirken kazara pakete girmesi kolay. Varsayılanı yayım dizininin dışına almak daha güvenli.
- **Idempotent değil:** `mac_pseudonymized: true` yazıyor ama girdide bu işareti kontrol etmiyor. Zaten takma adlandırılmış bir dosyaya ikinci kez uygulanırsa takma adları yeniden hash'ler. Üç satırlık bir koruma.

---

## 6. Diğer maddelerin durumu (R4 → R5)

| Madde | R4 | R5 |
|---|---|---|
| B1 "no device identity" düzeltmesi | ❌ | ✅ Açık öz-düzeltmeyle |
| B2 Abstract ≤200 kelime | ❌ 266 | ✅ **212** |
| B3 Pilot Modalias CI | ❌ | ✅ "44\%, 95\% CI [22,69]" eklendi |
| B5 Skorlayıcı ağırlıkları | ❌ | ✅ **Table I + §III-E** |
| B7 "Runnable tools dump data..." | ❌ | ✅ Kaldırılmış |
| A1 Evidence chain çalıştırma | ❌ | 🟡 Çalıştırıldı ama geçersiz arşiv (V1, V2) |
| A2 Pozitif kontrol | ❌ | ❌ **Yapılmadı** |
| A3 Artefakt yayımı | ❌ | 🟡 Araç hazır, dosya yok (P1) |
| M7-5 Algorithm 1 fazlalığı | ❌ | ❌ Üçüncü turdur açık |
| M7-7 Baseline doğrulanamaz | 🟡 | 🟡 Değişmedi |
| N4 Confidence terminolojisi | 🟡 | 🟡 **Şimdi daha net bir hata:** §III-E nümerik skoru *sürüme* eşliyor ve confidence'ı ayrı bir High/Med/Low etiketi olarak tanımlıyor; ama satır 430 hâlâ "The scanner does output a confidence score" diyor ve Tablo "Confidence score output" satırı taşıyor. Sürüm skoru ile confidence karıştırılıyor. |
| N5 Anonimlik | 🟡 | 🟡 Değişmedi (satır 54, 196, 679 + "authors'/researcher's" tutarsızlığı) |
| B3 kontrast testi / confound | ❌ | ❌ 8/18 vs 0/52 hâlâ test edilmiyor, confound (lokasyon/zaman/tur) adlandırılmıyor |
| N6b "Preliminary search" + 15 kaynak | 🟡 | 🟡 Değişmedi |
| N6c `ucsd2024firmware` basın bülteni | ❌ | ❌ Değişmedi |
| N6d Dempster–Shafer | ❌ | ❌ Değişmedi |

---

## 7. Full paper için kalan yol

### Zorunlu — 4 kalem

**Z1. Zincir çalıştırmasını geçerli kıl.** (V1 + V2) Güncel build ile üretilmiş kayıtlar üzerinde çalıştırın, **ve** "en az iki bağımsız sinyal taşıyan tarama sayısı"nı raporlayın. Bu sayı olmadan sonuç yorumlanamaz; bu sayıyla — tetiklenme sıfır çıksa bile — makale ampirik bir bulguya sahip olur. *Yeni veri toplamayı gerektirmez.*

**Z2. Table I'deki non-monotonluğu düzeltin.** (T1) LMP 10 satırı, kendi eşiklerinize göre BT 5.1 cihazlarını bir Android sürümü aşağı düşürüyor. Ayrıca 105 tavanı/kırpma belirsizliğini (T2) ve eksik eşikleri (T3) kapatın. *Bilinen bir hatayla full paper gönderilmez.*

**Z3. Pozitif kontrol.** (A2, iki turdur açık) Bilinen-erişilebilir tek bir cihaz, aynı boru hattı, tek oturum. Makalenin ana ampirik cümlesi (%88 never reached) bu kontrol olmadan askıda ve makale bunu kendisi kabul ediyor.

**Z4. Artefaktı üretin ve yayımlayın.** (P1–P3) `pseudonymize_macs.py`'yi çalıştırın, zaman damgalarını indirgeyin, `*_raw` alanlarını gözden geçirin, çıktıyı yayımlayın; tuz dosyasını yayım dizininin dışında tutun. Ayrıca baseline'ın sinyal/çıktı kümesini appendix olarak verin — Tablo II/III'ün M2 sütunu hâlâ doğrulanamıyor.

### Ucuz ama gerekli

**U1.** Fig. 1 ve Algorithm 1'deki "weighted score" etiketini düzeltin — sistem bir kural kaskadı, tek nümerik dalla. (F1)
**U2.** Algorithm 1'deki döngü/bağımsızlık fazlalığını giderin; `primary` semantiğini netleştirin. (A-1, A-2)
**U3.** N4: sürüm skoru ile confidence etiketini terminolojik olarak ayırın; satır 430 ve Tablo satırını düzeltin.
**U4.** V3: zincir arşivinin neden sweep verisinden farklı olduğunu bir cümleyle açıklayın.
**U5.** V5: eş-mevcudiyet tezini §V'in sonundan çıkarıp Abstract ve Conclusion'a taşıyın — makalenin en özgün bulgusu.
**U6.** 8/18 vs 0/52 için bir test verin ya da confound'u adlandırıp "direct empirical support"u yumuşatın.
**U7.** Dal öncelik sırasına gerekçe (T4); Dempster–Shafer paragrafı; `ucsd2024firmware` değişimi; literatür taramasının tamamlanması; anonimlik ve "authors'/researcher's" tutarlılığı.

### Değerlendirme

**Z1, Z2 ve Z4 mevcut kod ve veriyle kapanır; Z3 tek oturumluk bir deneydir.** Dördü tamamlandığında bu makale full paper olarak savunulabilir — ve V5'teki tez öne çıkarılırsa yalnızca savunulabilir değil, ilginç olur.

Şu haliyle **short paper / workshop için kabul edilebilir** durumda.

---

## 8. Hakem notu

Bu turda Table I'in açılması, incelemenin başından beri en çok tekrarlanan talebin — "sistemi görebilelim" — karşılığıydı, ve beklenen sonucu verdi: sistem görünür olur olmaz iki somut kusuru da görünür oldu (T1, T2). Bu, kötü bir haber değil; **şeffaflığın işe yaradığının kanıtı**. Yazarın non-monotonluğu kendisi işaret etmiş olması da aynı yönde. Ancak full paper eşiği burada değişir: bir kusur işaret edildiği için bağışlanmaz, düzeltildiği için bağışlanır.

Etik tarafı bu turda tamamlandı sayılabilir. Bir makalenin kendi önceki ifadesini "inaccurate" diye niteleyip düzeltmesi, ve takma adlandırmayı doğru kriptografik primitifle (tuzlu HMAC, çıplak hash değil) araçlaştırması, çoğu gönderiden ileridedir. Kalan iş operasyoneldir: aracı çalıştırmak ve arşivdeki diğer yeniden-tanımlama vektörlerini kapatmak.

Zincir çalıştırması ise iyi niyetli ama henüz boş: 43 kaydın 42'si test edilen yapıdan önce üretilmiş, dolayısıyla ortada bir null sonuç değil, bir duman testi var. Bunu geçerli kılmak — ve özellikle "kaç taramada iki bağımsız sinyal bir arada bulundu" sayısını vermek — makalenin en ilginç tezini ölçülmüş hale getirir: **bu araç sınıfında bağlayıcı kısıt sinyal kalitesi değil, sinyal eş-mevcudiyetidir.** Beş turdur biriken availability bulgularının hepsi o teze işaret ediyor; makale onu henüz kendi ana hikâyesi olarak sahiplenmedi.
