from django.db import models

class Competition(models.Model):
    """
    FI: Kilpailun perusmetatiedot (nimi, päivä, paikka). GDPR: ei henkilötietoja.
    EN: Core metadata for a competition (name, date, location). No personal data.
    """
    # FI: Nimi ja päivämäärä riittävät yksilöimään useimmat kisat.
    # EN: Name and date are enough to uniquely identify most events.
    name = models.CharField(max_length=200)
    date = models.DateField()

    def __str__(self) -> str:
        # FI: Näytetään nimi ja päivämäärä listauksissa/adminissa (kun kentät lisätty).
        # EN: Friendly display in lists/admin (once fields exist).
        return getattr(self, "name", "Competition")
