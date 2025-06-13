# ORAOwl – Toteutus- ja raportointisuunnitelma

Tämä dokumentti toimii tiekarttana ORAOwl-projektin tekniselle toteutukselle ja opinnäytetyön raportoinnille. Voit merkitä rastilla tehdyt tehtävät. Lopullisena tavoitteena on valmis ja dokumentoitu sovellus joulukuussa 2025.

---

## ✅ = Tehty ☐ = Tekemättä 🛠 = Työn alla

---

## VAIHE 1: Projektin aloitus (Toukokuu)
- [x] ✅ Luo GitHub-repositorio ja lisää `.gitignore` sekä `README.md`
- [x] ✅ Alusta Django-projekti (`oraowl`) ja `oraw-app`
- [x] ✅ Luo `.env`-tiedosto ja ota käyttöön `django-environ`
- [ ] Kirjoita raportin alkuun Johdanto-luku luonnosmuotoon
- [ ] Kirjaa tekninen tavoite, ongelman kuvaus ja toimeksiantaja

---

## VAIHE 2: Käyttöliittymäpohja ja teknologiat (Toukokuu)
- [x] ✅ Integroi AdminLTE + Bootstrap, luo `base.html`
- [x] ✅ Luo sivupohjat: `home.html`, `login.html`, `register.html`, jne.
- [ ] Kirjoita raporttiin käytettävät teknologiat ja työkalut
- [ ] Perustele valinnat: miksi Django, miksi Bootstrap

---

## VAIHE 3: Tietokantamalli ja IOFXML-parseri (Kesäkuu)
- [ ] Suunnittele tietomallit: `Runner`, `Competition`, `Result`, `UploadedFile`
- [ ] Toteuta XML-parseri ElementTreellä (`utils/parser.py`)
- [ ] Testaa parseri yhdellä tulostiedostolla
- [ ] Raportoi tietomallin rakenne, parserin toiminta ja testisyötteet

---

## VAIHE 4: Käyttäjähallinta ja kirjautuminen (Kesäkuu)
- [ ] Toteuta käyttäjien rekisteröinti, kirjautuminen ja profiilinäkymä
- [ ] Lisää roolit: normaali käyttäjä, organisaatio (`is_staff`)
- [ ] Kirjoita raporttiin käyttäjähallinnan rakenne ja roolien toiminta

---

## VAIHE 5: Hakutoiminnot ja selailu (Heinäkuu)
- [ ] Luo hakutoiminto (nimi, seura, kilpailu, sarja, emit/SI-numero)
- [ ] Näytä kilpailujen ja suunnistajien tulokset käyttöliittymässä
- [ ] Raporttiin hakulogiikka ja näkymäesimerkit

---

## VAIHE 6: Visualisointi ja analytiikka (Elokuu)
- [ ] Toteuta kehityskaaviot (km/min vs. aika) ja vertailunäkymät
- [ ] Käytä Matplotlib tai Plotly
- [ ] Kirjoita raporttiin analyysimenetelmät ja esimerkkikaaviot

---

## VAIHE 7: GDPR ja tietosuoja (Syyskuu)
- [ ] Laadi `privacy.html` ja `terms.html`
- [ ] Toteuta anonymisointitoiminto (käyttäjän pyynnöstä)
- [ ] Kirjoita raporttiin tietosuojan huomiointi ja GDPR-selvitys

---

## VAIHE 8: Arviointi, testaus ja julkaisu (Lokakuu)
- [ ] Toteuta yksikkötestit (parseri, lomakkeet)
- [ ] Julkaise demo esim. Renderiin tai Tietoketulle
- [ ] Kirjoita raporttiin arviointiluku: onnistumiset, haasteet, jatkokehitys

---

## VAIHE 9: Dokumentointi ja viimeistely (Lokakuu–Marraskuu)
- [ ] Viimeistele raportin kaikki luvut, lisää tiivistelmä ja lähteet
- [ ] Tee kuvaliitteet, kaaviot ja liitä lähdekoodi osaksi liitteitä
- [ ] Palauta raportti ja valmistele esitys

---

> **Muista:** Päivitä tätä tiedostoa aktiivisesti projektin edetessä, jotta kaikilla tiimin jäsenillä on selkeä näkymä työn etenemisestä.
