
# oraw_app/forms.py
from __future__ import annotations

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.conf import settings


# ============================================================================
# Signup form / Rekisteröintilomake
# ============================================================================
class SignupForm(UserCreationForm):
    """
    FI: Rekisteröintilomake, jossa sähköposti on pakollinen ja lomaketason
        tarkistus estää duplikaattisähköpostit.
    EN: Signup form with required email and a form-level uniqueness check.
    """

    email = forms.EmailField(
        label="Sähköpostiosoite",
        required=True,
        help_text="Käytä toimivaa sähköpostiosoitetta (salasanan palautusta varten).",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control w-100",
                "style": "width:100%",
                "placeholder": "esim. etunimi.sukunimi@esimerkki.fi",
                "autocomplete": "email",
            }
        ),
        validators=[validate_email],
    )

    class Meta:
        model = User
        # FI: UserCreationForm hoitaa password1/2-kentät.
        # EN: UserCreationForm provides password1/2 fields automatically.
        fields = ("username", "email")

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # ------------------------------------------------------------------
        # FI: Kenttien otsikot (labelit) suomeksi
        # EN: Field labels in Finnish
        # ------------------------------------------------------------------
        self.fields["username"].label = "Käyttäjätunnus"
        self.fields["password1"].label = "Salasana"
        self.fields["password2"].label = "Vahvista salasana"

        # ------------------------------------------------------------------
        # FI: Yhtenäinen ulkoasu ja placeholderit
        # EN: Consistent styles and placeholders
        # ------------------------------------------------------------------
        self.fields["username"].widget.attrs.update(
            {
                "class": "form-control w-100",
                "style": "width:100%",
                "placeholder": "esim. etunimi.sukunimi",
                "autocomplete": "username",
                "autofocus": "autofocus",
            }
        )
        self.fields["password1"].widget.attrs.update(
            {
                "class": "form-control w-100",
                "style": "width:100%",
                "placeholder": "Vähintään 8 merkkiä",
                "autocomplete": "new-password",
            }
        )
        self.fields["password2"].widget.attrs.update(
            {
                "class": "form-control w-100",
                "style": "width:100%",
                "placeholder": "Syötä salasana uudelleen",
                "autocomplete": "new-password",
            }
        )

    def clean_email(self):
        """
        FI: Varmistaa, ettei samaa sähköpostiosoitetta ole jo käytössä.
        EN: Ensures the email address is not already in use.
        """
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Tällä sähköpostilla on jo tili.")
        return email


# ============================================================================
# IOFXML upload form / IOFXML-latauslomake
# ============================================================================
class IOFXMLUploadForm(forms.Form):
    """
    FI: Lomake IOFXML 3.0 ResultList -tiedoston lataamiseen ja tuontiin.
    EN: Form for uploading and importing an IOFXML 3.0 ResultList file.
    """

    file = forms.FileField(
        label="IOFXML ResultList -tiedosto",
        help_text=(
            "FI: Valitse IOF Data Standard 3.0 ResultList -tiedosto (XML). "
            "EN: Select an IOF Data Standard 3.0 ResultList XML file."
        ),
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control",
            }
        ),
    )

    note = forms.CharField(
        label="Muistiinpano (valinnainen) / Note (optional)",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": (
                    "FI: Kirjaa halutessasi lyhyt kuvaus latauksesta. "
                    "EN: Optionally add a short note about this upload."
                ),
            }
        ),
        help_text=(
            "FI: Tämä kenttä on vain dokumentointia varten, eikä vaikuta tuontiin. "
            "EN: This field is for documentation only and does not affect the import."
        ),
    )
