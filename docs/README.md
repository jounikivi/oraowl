````md
# ORAOwl – Orienteering Results Archive

**ORAOwl** on Django-pohjainen sovellus suunnistustulosten arkistointiin, analysointiin ja vertailuun.  
Projektin tavoitteena on tarjota yhtenäinen alusta IOF XML -tulosten lataamiseen, selaamiseen ja jatkokehityksessä myös suunnistajan kehityksen analysointiin.

Sovellus toimii osana opinnäytetyötä ja kehittyy vaiheittain dokumentoidun suunnittelun mukaisesti.

---

## 🚀 Käyttöönotto (Development Setup)

### 1. Kloonaa repositorio
```bash
git clone https://github.com/KAYTTAJANIMESI/oraowl.git
cd oraowl
````

### 2. Luo ja aktivoi virtuaaliympäristö (Windows)

```bash
python -m venv venv
venv\Scripts\activate
```

macOS / Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Asenna projektin riippuvuudet

```bash
pip install -r requirements.txt
```

### 4. Luo `.env`-tiedosto

Luo projektin juureen `.env`-tiedosto ja syötä vähintään seuraavat:

```env
SECRET_KEY=lisää-tähän-salainen-avain
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
```

### 5. Suorita migraatiot

```bash
python manage.py migrate
```

### 6. Käynnistä kehityspalvelin

```bash
python manage.py runserver
```

Sovellus on nyt käytettävissä osoitteessa:
👉 [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 🧩 Keskeiset teknologiat

* **Python 3.x**
* **Django 5.2.x**
* **django-environ**
* **SQLite** (kehityksessä)
* **Bootstrap 5 + AdminLTE** (käyttöliittymä)
* **Matplotlib / Plotly** (visualisointi, myöhemmin)
* **IOF Data Standard 3.0** (XML-tulokset)

---

## 📦 Projektin rakenne

| Hakemisto / tiedosto | Kuvaus                                               |
| -------------------- | ---------------------------------------------------- |
| `oraowl/`            | Projektikonfiguraatio (settings, URL-reititys)       |
| `oraw_app/`          | Sovelluslogiikka: mallit, näkymät, importer, parseri |
| `oraw_app/utils/`    | IOFXML-parseri ja -importteri                        |
| `oraw_app/models/`   | Tietokantamallit                                     |
| `.env`               | Ympäristömuuttujat                                   |
| `requirements.txt`   | Riippuvuudet                                         |
| `README.md`          | Dokumentaatio                                        |

---

## 👥 Tekijät

* **Jouni Kiviperä**
* **Atte Stenroos**



