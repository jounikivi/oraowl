# oraw_app/forms.py
from __future__ import annotations
from django import forms

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class UploadIOFXMLForm(forms.Form):
    """
    FI: Yksinkertainen lomake IOFXML-tiedoston lataamiseen.
        Hyväksyy yhden IOF XML 3.0/3.1 ResultList -tiedoston.

    EN: Simple form for uploading a single IOF XML 3.0/3.1 ResultList file.
    """
    iofxml_file = forms.FileField(
        label="IOFXML file",
        help_text="Select a valid IOF XML 3.0/3.1 ResultList file.",
    )




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

        # FI: Labelit suomeksi.
        # EN: Finnish labels for fields.
        self.fields["username"].label = "Käyttäjätunnus"
        self.fields["password1"].label = "Salasana"
        self.fields["password2"].label = "Vahvista salasana"

        # FI: Yhtenäiset Bootstrap-luokat ja placeholderit.
        # EN: Consistent Bootstrap classes and placeholders.
        self.fields["username"].widget.attrs.update(
            {"class": "form-control", "placeholder": "esim. etunimi.sukunimi",
             "autocomplete": "username"}
        )
        self.fields["password1"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Vähintään 8 merkkiä",
             "autocomplete": "new-password"}
        )
        self.fields["password2"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Syötä salasana uudelleen",
             "autocomplete": "new-password"}
        )
