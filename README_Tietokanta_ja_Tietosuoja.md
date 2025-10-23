```markdown
# 🗄️ ORAOwl – Tietokanta- ja tietosuojadokumentaatio

## 1. Johdanto

Tämä dokumentaatio kuvaa ORAOwl-järjestelmän tietokantarakenteen, tietosuojakäytännöt ja GDPR-yhteensopivuuden.  
Järjestelmä on rakennettu **Django-kehyksellä** ja sen tarkoitus on tarjota suunnistustulosten arkistointi- ja analysointipalvelu.

Kaikki tietomallit sijaitsevat sovelluksessa `oraw_app`, ja noudattavat yhtenäistä nimeämis- ja koodauskäytäntöä:
- **Kaikki koodi englanniksi**
- **Dokumentointi suomeksi**
- **Kenttien nimet selkeitä ja kuvaavia**
- **Kaikki mallit sisältävät luonti- ja muokkausajat (`created_at`, `updated_at`)**

---

## 2. Tietokantarakenne

### 2.1 Ydintaulut

| Malli | Kuvaus | Tärkeimmät kentät |
|--------|--------|------------------|
| **Athlete** | Suunnistaja (henkilö, joka osallistuu kilpailuihin). | `first_name`, `last_name`, `club`, `gender`, `year_of_birth`, `public_alias`, `is_public` |
| **Competition** | Kilpailutapahtuma. | `name`, `date`, `location`, `organizer`, `source_file` |
| **Course** | Rata tai sarja kilpailussa. | `competition`, `name`, `length_km` |
| **Result** | Yksittäisen urheilijan tulos kilpailussa. | `athlete`, `course`, `competition`, `status`, `position`, `total_time_s`, `is_public` |
| **Split** | Rastiväli (väliaikatieto). | `result`, `seq`, `control_code`, `split_time_s`, `cum_time_s`, `notes`, `created_at`, `updated_at` |

### 2.2 Tukitaulut

| Malli | Kuvaus |
|--------|--------|
| **ControlCard** | Kilpailukortti (esim. Emit tai SportIdent). |
| **AthleteIdentifier** | Mahdollistaa useita tunnisteita yhdelle urheilijalle (kortit, RFID jne.). |
| **PrivacyPreference** | Urheilijan tietosuojavalinnat (GDPR). |
| **AuditLog** | Kirjaa kaikki tietosuojaan liittyvät muutokset. |
| **UploadedFile** | Tallennetut IOF XML -tiedostot, joilla on säilytysaika (`retention_until`). |

### 2.3 Tietokantasuhteet

```

Athlete 1 ────< Result >──── 1 Course
│                        │
│                        v
└──────< PrivacyPreference  >──── AuditLog
│
└── GDPR-lokit (anonymisointi, muutokset)

Result 1 ────< Split

````

---

## 3. GDPR ja tietosuoja

ORAOwl täyttää **EU:n yleisen tietosuoja-asetuksen (GDPR 2016/679)** vaatimukset.  
Tietosuoja on toteutettu teknisesti, organisatorisesti ja kooditasolla.

### 3.1 Tietosuojaperiaatteet

| Periaate | Käytännön toteutus |
|-----------|--------------------|
| **Tietojen minimointi** | Tallennetaan vain kilpailutoiminnan kannalta välttämättömät henkilötiedot (nimi, sukupuoli, seura). |
| **Läpinäkyvyys** | Käyttäjälle tarjotaan tietosuojaseloste (`privacy.html`). |
| **Oikeus tulla unohdetuksi** | Jos urheilija ei halua tietojensa näkyvän, `is_public=False` ja `PrivacyPreference.show_name=False` → nimi korvataan sanalla *“Anonyymi”*. |
| **Lokitus ja todennettavuus** | Kaikki muutokset kirjataan `AuditLog`-tauluun. |
| **Tietojen oikaisu ja poistaminen** | Admin voi poistaa tai anonymisoida urheilijan tietoja hallintapaneelissa. |
| **Tietojen säilytys** | `UploadedFile`-mallin `retention_until`-kenttä määrittää tiedoston poistopäivän. |

### 3.2 Tietosuojan tekninen toteutus

**Athlete.display_name()**
```python
def display_name(self):
    if not self.is_public:
        return "Anonyymi"
    return f"{self.first_name} {self.last_name}".strip()
````

**PrivacyPreference**

```python
class PrivacyPreference(models.Model):
    athlete = models.OneToOneField(Athlete, on_delete=models.CASCADE, related_name="privacy")
    show_name = models.BooleanField(default=True)
    allow_public_stats = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**AuditLog**

```python
class AuditLog(models.Model):
    athlete = models.ForeignKey(Athlete, on_delete=models.CASCADE, related_name="privacy_audit_logs")
    action = models.CharField(max_length=64)  # esim. "hide", "anonymize"
    by = models.CharField(max_length=64)
    details = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

---

## 4. Käyttöohjeet tietokannan hallintaan

### 4.1 Migraatiot ja kehityspalvelin

Luo ja päivitä tietokanta:

```bash
python manage.py makemigrations
python manage.py migrate
```

Käynnistä kehityspalvelin:

```bash
python manage.py runserver
```

Avaa admin-paneeli osoitteessa:

```
http://127.0.0.1:8000/admin
```

### 4.2 Datan tuonti IOF XML -tiedostosta

```bash
python manage.py import_iofxml --file tulokset.xml
```

Tämä luo automaattisesti seuraavat tietueet:

* Competition
* Course
* Athlete
* Result
* Split

Kaikki validointi tehdään automaattisesti.

---

## 5. Tietokannan tyhjennys ja ylläpito

**Esikatselu (dry-run):**

```bash
python manage.py reset_oraw_app --dry-run
```

**Tyhjennys (säilyttää admin-käyttäjät):**

```bash
python manage.py reset_oraw_app --yes-i-really-mean-it
```

Tämä komento poistaa kaikki `oraw_app`-tietueet, mutta **säilyttää käyttäjähallinnan (admin/auth)**.
SQLite-tietokannassa suoritetaan automaattisesti myös `VACUUM`, joka optimoi tietokannan koon.

---

## 6. Testaus ja laadunvarmistus

Suorita kaikki testit:

```bash
pytest -q
```

Odotettu tulos:

```
..... [100%]
5 passed
```

Testit kattavat:

* IOF XML -tuonnin
* GDPR-asetukset ja anonymisoinnit
* AuditLog-lokit
* Split- ja Result -mallien tietojen eheys

---

## 7. Yhteenveto

✅ **Tietokanta on modulaarinen, skaalautuva ja PostgreSQL-yhteensopiva.**
✅ **GDPR 2025 -yhteensopivuus on varmistettu** (anonymisointi, lokitus, säilytys).
✅ **Kaikki testit läpäisevät automaattisesti (pytest).**
✅ **Tietojen tuonti, anonymisointi ja hallinta onnistuvat hallintapaneelista.**
✅ **Tietokanta voidaan nollata turvallisesti ilman admin-käyttäjien menetystä.**

---

## 8. Jatkokehitys

* PostgreSQL siirtyminen tuotantoon
* Tietojen automaattinen anonymisointi säilytysajan jälkeen
* REST API -rajapinta tulosten hakuun
* Admin-työkalut massapoistoon ja anonymisointiin

---

📄 **Dokumentti:** README_Tietokanta_ja_Tietosuoja.md
📅 **Päivitetty:** 23.10.2025
👤 **Laatija:** Jouni Kiviperä
🏫 **Turun ammattikorkeakoulu – Tietojenkäsittely (Tradenomi)**
📘 **Projekti:** ORAOwl – Orienteering Results Archive

```
