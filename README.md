# ORAOwl https://oraowl.fi/

**ORAOwl** on Django-pohjainen sovellus suunnistustulosten arkistointiin, analysointiin ja vertailuun.  
Projekti toimii opinnäytetyönä ja toteutetaan vaiheittain dokumentoidun suunnitelman mukaan.

---

## 🔧 Kehitysympäristön käyttöönotto

1. **Kloonaa repositorio**
```bash
git clone https://github.com/KAYTTAJANIMESI/oraowl.git
cd oraowl
```

2. **Luo ja aktivoi virtuaaliympäristö (Windows)**
```bash
python -m venv venv
venv\Scripts\activate
```

3. **Asenna riippuvuudet**
```bash
pip install -r requirements.txt
```

4. **Luo `.env`-tiedosto**
- Luo tiedosto projektin juureen
- Käytä mukana olevaa mallia: `.env`

📄 `.env`:
```env
SECRET_KEY=lisää-tähän-salainen-avain
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
```

5. **Käynnistä kehityspalvelin**
```bash
python manage.py runserver
```

Avaa selaimessa: http://127.0.0.1:8000

---

## 📦 Teknologiat

- Python 3.x
- Django 5.2.x
- django-environ
- SQLite (kehityskäytössä)
- Bootstrap + AdminLTE (käyttöliittymä)
- Matplotlib / Plotly (visualisointiin, myöhemmin)

---

## 📁 Projektin rakenne

| Kohde             | Kuvaus                                  |
|-------------------|------------------------------------------|
| `oraowl/`         | Projektin ydin (asetukset, reititys)    |
| `oraw_app/`       | Sovelluslogiikka (tietomallit, näkymät) |
| `.env`            | Mallipohja .env-tiedostolle             |
| `requirements.txt`| Riippuvuudet                            |
| `README.md`       | Tämä ohje                               |

---

## 👥 Tekijät

- Jouni Kiviperä
- Atte Stenroos
