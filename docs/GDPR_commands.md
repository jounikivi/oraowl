# GDPR-komennot ja admin-toiminnot

Tämä tiedosto kokoaa kaikki sovellukseen lisätyt GDPR-työkalut.

## 1. Management commands

### anonymize_athlete (esimerkki, jos lisätään)
```bash
python manage.py anonymize_athlete --id <athlete_uuid>
```
- **FI:** Anonymisoi yhden urheilijan tiedot (nimi piilotetaan, alias = "Anonyymi").
- **EN:** Anonymizes one athlete’s data (hide name, alias = "Anonyymi").

---

### anonymize_card (esimerkki, jos lisätään)
```bash
python manage.py anonymize_card --uid <controlcard_uid>
```
- **FI:** Poistaa leimauskortin liitoksen urheilijoihin ja tuloksiin.
- **EN:** Removes control card links from athletes and results.

---

### purge_uploadedfiles
```bash
python manage.py purge_uploadedfiles
```
- **FI:** Poistaa kaikki `UploadedFile`-rivit, joiden `retention_until` on menneisyydessä.  
  Poistaa samalla myös levyllä olevan XML-tiedoston (jos storage konffattu).  
- **EN:** Deletes all `UploadedFile` rows with `retention_until` in the past.  
  Also deletes the physical file if storage is configured.

---

## 2. Admin-toiminnot

### Anonymize selected athletes (GDPR)
- **FI:** Asettaa valituille urheilijoille `is_public=False` ja `public_alias="Anonyymi"`.  
  Näin henkilön nimi ei näy julkisissa näkymissä.  
- **EN:** Sets `is_public=False` and `public_alias="Anonyymi"` for selected athletes.  
  Hides identity in public views.

---

### Clear control cards for selected results (GDPR)
- **FI:** Tyhjentää `control_card`-kentän valituista tuloksista.  
  Käytetään, jos urheilija pyytää korttitietojensa poistamista.  
- **EN:** Clears `control_card` field from selected results.  
  Used if an athlete requests removal of their control card data.

---

## 3. Käyttöohjeet

1. **Admin-paneeli:**  
   - Käytä bulk-toimintoja (Anonymize athletes, Clear control cards) yksittäisiin pyyntöihin.
2. **Komentorivi:**  
   - Aja `purge_uploadedfiles` säännöllisesti (esim. kerran kuussa), jotta vanhat tiedostot poistuvat.
3. **Dokumentointi:**  
   - Kaikki ajot kannattaa kirjata ylläpidon lokiin (päivämäärä, mitä poistettiin)
