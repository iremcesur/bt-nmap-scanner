# Request to the THM Data Protection Officer — ready to send

Prepared 2026-09-10, **revised 2026-09-13** after a second, deeper collection
was discovered that the first version did not describe. **Not sent** — send it
yourself; I have no authenticated mail access.

> **Do not send the 2026-09-10 wording.** It described only the 52-address
> Layer 1--2 sweep. A separate archive of 31 full scans against 21 devices, 12
> of them third-party, was found on 2026-09-13: it had been written to a
> different working directory and was not known about. Those scans opened live
> connections and profiled permissions, and retained advertised names that
> contain people's given names. Sending the old wording would understate the
> processing to the officer whose job is to assess exactly that.

Fill in every `[...]` before sending. Do not guess at the ethics-committee
details; if you do not know whether THM's committee covers this kind of study,
say so in the mail and let the DPO route it.

**Send it today.** It is the one item on the critical path that is not in your
hands: everything else for the 22 October ICISSP deadline can proceed in
parallel, but a paper submitted without this can be desk-rejected by security
venues regardless of its technical content.

---

## Suggested recipients

- `datenschutz@thm.de` — THM Data Protection Officer **[verify this address on
  the THM site before sending; I have not confirmed it]**
- cc: your supervisor
- cc: the ethics committee contact, if THM has one for non-medical research
  **[unknown to me]**

Subject: **Nachträgliche datenschutzrechtliche Bewertung — Bluetooth-Messstudie
(Signalverfügbarkeit), Anfrage um schriftliche Stellungnahme**

---

## German version (primary)

Sehr geehrte Damen und Herren,

ich bin [Name], [Position/Matrikelnummer], am Fachbereich [Fachbereich] der THM,
betreut von [Betreuer:in]. Ich bitte um eine **schriftliche
datenschutzrechtliche Stellungnahme** zu einer bereits durchgeführten Messung,
die ich als Grundlage für eine wissenschaftliche Veröffentlichung benötige.

**Worum es geht.** Es handelt sich um **zwei** Erhebungen unterschiedlicher
Eingriffstiefe. Ich schildere beide, auch die zweite, die mir bei der ersten
Fassung dieses Schreibens nicht bekannt war.

*(1) Verfügbarkeitsmessung.* Am 31.08.2026 habe ich in [Ort] 52 sichtbare
Bluetooth-Geräte abgefragt. Erhoben wurde ausschließlich, **welche technischen
Signale ein Gerät überhaupt preisgibt**. Gespeichert wurden MAC-Adresse,
Anzeigename und pro Signal ein Vorhanden/Nicht-vorhanden-Vermerk.

*(2) Vollständige Scans — deutlich eingriffsintensiver.* Daneben wurden **31
vollständige Scans gegen 21 Geräte** durchgeführt, davon **12 fremde Geräte**.
Dabei wurde jeweils eine **aktive Verbindung aufgebaut** und zusätzlich
erhoben: Round-Trip-Latenz, Betriebsdauer des Hosts, Kopplungs-Sicherheitslage,
AFH-Kanalkarte, ein MTU-Fragmentierungstest mit 600 Byte sowie ein Profil
darüber, **welche Bluetooth-Profil-Berechtigungen der Host gewähren würde**
(z. B. Kontakte, Mikrofon). Die Anzeigenamen wurden im Klartext gespeichert;
mehrere enthalten **Vornamen natürlicher Personen**.

In **keinem** Fall erfolgte eine Layer-3-Verhaltensbeobachtung, eine Kopplung,
eine Authentifizierung oder eine Erhebung von Inhalten.

Dass mir die zweite Erhebung zunächst entgangen ist, liegt an einem
technischen Fehler unsererseits: das Scan-Archiv wurde in ein relativ
adressiertes Verzeichnis geschrieben und lag dadurch getrennt vom geprüften
Datenbestand. Der Fehler ist behoben.

**Der Punkt, auf den ich Sie ausdrücklich hinweisen möchte.** Die Erhebung fand
**vor** einer institutionellen Prüfung statt, nicht danach. Das ist die falsche
Reihenfolge, und ich möchte das nicht nachträglich anders darstellen. Ich bitte
deshalb nicht um eine Genehmigung im Nachhinein, sondern um Ihre Bewertung der
tatsächlichen Lage.

**Was ich bereits umgesetzt habe:**
- Alle Archive sind pseudonymisiert (HMAC-SHA256 mit geheimem Salt); nur die
  pseudonymisierten Fassungen sind für eine Veröffentlichung vorgesehen.
- Ein automatischer Prüflauf verhindert die Freigabe, solange noch eine
  MAC-Adresse oder ein Gerätename enthalten ist.
- Ein Löschkonzept mit Fristen liegt vor (Rohdaten und Salt: Löschung bis
  spätestens 31.03.2027).

**Meine konkreten Fragen:**
1. Auf welche **Rechtsgrundlage** stützt sich diese Verarbeitung an der THM —
   Art. 6 Abs. 1 lit. f oder lit. e i. V. m. Art. 89 DSGVO?
2. Ist die Erhebung angesichts der nachträglichen Prüfung aus Ihrer Sicht
   **zulässig**, oder sind die Rohdaten zu löschen? Bitte bewerten Sie
   Erhebung (1) und (2) **getrennt** — sie unterscheiden sich erheblich in
   der Eingriffstiefe, und ich möchte kein günstigeres Ergebnis für (2)
   ableiten, als es für sich genommen verdient.
3. Sind die vorgeschlagenen **Löschfristen** angemessen?
4. Ist die **Veröffentlichung** des pseudonymisierten Datensatzes vertretbar?
   Mir ist bewusst, dass Pseudonymisierung bei n ≈ 50 an einem einzigen Ort
   keine Anonymisierung ist.
5. Welche **Kontaktadresse** soll ich für Betroffenenrechte angeben?
6. Benötigt eine **künftige** Messung dieser Art eine Vorabprüfung, und wenn
   ja, bei wem?

Für die Einreichung benötige ich Ihre Antwort möglichst bis **[Datum,
realistisch: 2026-10-08]** — die Deadline ist der 22.10.2026. Gern erläutere
ich das Vorgehen in einem kurzen Termin und stelle den Messcode sowie das
Löschkonzept vollständig zur Verfügung.

Mit freundlichen Grüßen
[Name] · [Kontakt]

---

## English version (attach or send if the office prefers English)

Dear Data Protection Officer,

I am [name], [role] in the Department of [department] at THM, supervised by
[supervisor]. I am requesting a **written data protection assessment** of a
measurement I have already carried out, which I need before submitting it for
publication.

**What it was.** There were **two** collections of different intrusiveness. I
describe both, including the second, which I was not aware of when this letter
was first drafted.

*(1) Availability measurement.* On 2026-08-31 in [location] I queried 52
visible Bluetooth devices, recording only **which technical signals a device
exposes at all**: MAC address, advertised name, and a present/absent marker
per signal.

*(2) Full scans — substantially more intrusive.* Separately, **31 full scans
were run against 21 devices, 12 of them third-party**. Each opened an **active
connection** and additionally measured round-trip latency, host uptime,
pairing security posture, the adaptive frequency-hopping channel map, and a
600-byte MTU fragmentation probe, and derived a profile of **which Bluetooth
profile permissions the host would grant** (contacts, microphone, and so on).
Advertised names were stored in cleartext; several contain **the given names
of natural persons**.

In no case was there Layer-3 behavioral observation, pairing, authentication,
or collection of content.

The reason the second collection escaped the first version of this letter is a
technical fault on our side: the scan archive was written to a
relatively-addressed directory and therefore sat apart from the data under
review. That has been corrected.

**The point I want to put in front of you directly.** Collection happened
**before** institutional review, not after. That is the wrong order, and I do
not want to present it as anything else. I am therefore not asking for
retrospective approval, but for your assessment of the actual situation.

**Already done:** all archives pseudonymized (HMAC-SHA256 under a secret salt);
an automated gate blocks release while any MAC or device name survives; a
deletion schedule is in place (raw data and salt deleted by 2027-03-31).

**My questions:**
1. Which **legal basis** applies at THM — Art. 6(1)(f), or 6(1)(e) with Art. 89?
2. Given the retrospective review, is the collection **lawful**, or must the raw
   data be deleted? Please assess collections (1) and (2) **separately** —
   they differ substantially in intrusiveness, and I do not want a favourable
   finding for (1) to be read across to (2).
3. Are the proposed **retention periods** appropriate?
4. Is **publishing** the pseudonymized dataset defensible? I am aware that at
   n ≈ 50 in a single location, pseudonymization is not anonymization.
5. What **contact address** should I state for data subject rights?
6. Does a **future** measurement of this kind require prior review, and by whom?

I would need your response by **[date — realistically 2026-10-08]**; the
submission deadline is 2026-10-22. I am happy to walk through the method in a
short meeting and can provide the measurement code and the deletion plan in
full.

Kind regards,
[name] · [contact]

---

## Two things not to do in this mail

1. **Do not soften the ordering.** "Ethics review is under way" reads as
   concealment if the dates surface later. The dates are in the archive
   timestamps and in git history.
2. **Do not promise the raw data is anonymous.** It is pseudonymized personal
   data and stays in scope of the GDPR. Claiming otherwise to a DPO is the one
   claim they are guaranteed to check.
