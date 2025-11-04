# oraw_app/forms.py
from __future__ import annotations
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


# ---------------------------------------------------------------------------
# IOFXML Upload Form
# ---------------------------------------------------------------------------

class UploadIOFXMLForm(forms.Form):
    """
    FI: Yksinkertainen lomake IOFXML-tiedoston lataamiseen.
        Hyväksyy yhden IOF XML 3.0/3.1 ResultList -tiedoston.

    EN: Simple form for uploading a single IOF XML 3.0/3.1 ResultList file.
    """

    iofxml_file = forms.FileField(
        label="IOFXML-tiedosto",
        help_text="Valitse voimassa oleva IOF XML 3.0/3.1 ResultList -tiedosto.",
    )


# ---------------------------------------------------------------------------
# Rekisteröintilomake (Signup Form)
# ---------------------------------------------------------------------------

class SignupForm(UserCreationForm):
    """
    FI: Rekisteröintilomake suomenkielisillä otsikoilla ja siisteillä kentillä.
    EN: Signup form with Finnish labels and styled inputs.
    """

    class Meta:
        model = User
        fields = ("username",)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # -------------------------------------------------------------------
        # Kenttien otsikot suomeksi
        # -------------------------------------------------------------------
        self.fields["username"].label = "Käyttäjätunnus"
        self.fields["password1"].label = "Salasana"
        self.fields["password2"].label = "Vahvista salasana"

        # -------------------------------------------------------------------
        # Kenttien tyyli ja placeholderit
        # -------------------------------------------------------------------
        self.fields["username"].widget.attrs.update({
            "class": "form-control w-100",
            "placeholder": "esim. etunimi.sukunimi",
            "autocomplete": "username",
            "autofocus": "autofocus",
        })
        self.fields["password1"].widget.attrs.update({
            "class": "form-control w-100",
            "placeholder": "Vähintään 8 merkkiä",
            "autocomplete": "new-password",
        })
        self.fields["password2"].widget.attrs.update({
            "class": "form-control w-100",
            "placeholder": "Syötä salasana uudelleen",
            "autocomplete": "new-password",
        })
