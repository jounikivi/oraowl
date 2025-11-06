# oraw_app/forms.py
from __future__ import annotations

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator


# ============================================================================
# IOFXML upload form / IOFXML-latauslomake
# ============================================================================
class UploadIOFXMLForm(forms.Form):
    """
    FI: Lomake IOF XML 3.0/3.1 -tiedoston lataamiseen. 
        Tarkistaa tiedoston koon ja tyypin ennen käsittelyä.
    EN: Form for uploading a single IOF XML 3.0/3.1 ResultList file.
        Performs basic validation for file type and size.
    """

    iofxml_file = forms.FileField(
        label="IOFXML-tiedosto",
        help_text="Valitse IOF XML 3.0/3.1 ResultList -muotoinen tiedosto.",
        validators=[FileExtensionValidator(allowed_extensions=["xml"])],
        widget=forms.ClearableFileInput(attrs={"accept": ".xml,application/xml"}),
    )

    def clean_iofxml_file(self):
        """
        FI: Tarkistaa, että ladattu tiedosto ei ole tyhjä ja ettei se ylitä kokorajaa.
        EN: Validates that the uploaded file is not empty and does not exceed size limit.
        """
        f = self.cleaned_data["iofxml_file"]
        max_mb = 10
        if f.size == 0:
            raise forms.ValidationError("Tiedosto on tyhjä.")
        if f.size > max_mb * 1024 * 1024:
            raise forms.ValidationError(f"Tiedosto on liian suuri (> {max_mb} Mt).")
        return f


# ============================================================================
# Signup form / Rekisteröintilomake
# ============================================================================# ============================================================================
# Signup form / Rekisteröintilomake
# ============================================================================
from django.core.validators import validate_email  # add this import near others

class SignupForm(UserCreationForm):
    """
    FI: Rekisteröintilomake, jossa sähköposti on pakollinen ja
        lomaketason tarkistus estää duplikaattisähköpostit.
    EN: Signup form with required email and form-level uniqueness check.
    """

    email = forms.EmailField(
        label="Sähköpostiosoite",
        required=True,
        help_text=(
            "Käytä toimivaa sähköpostiosoitetta (salasanan palautusta varten)."
        ),
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
        # FI: Näytettävien kenttien järjestys lomakkeella.
        # EN: Field order on the form.
        fields = ("username", "email")

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # --------------------------------------------------------------------
        # FI: Kenttien otsikot (labelit) suomeksi
        # EN: Field labels in Finnish
        # --------------------------------------------------------------------
        self.fields["username"].label = "Käyttäjätunnus"
        self.fields["password1"].label = "Salasana"
        self.fields["password2"].label = "Vahvista salasana"

        # --------------------------------------------------------------------
        # FI: Yhtenäinen ulkoasu ja placeholderit
        # EN: Consistent styles and placeholders
        # --------------------------------------------------------------------
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
        FI: Varmistaa, ettei samaa sähköpostia ole jo käytössä.
        EN: Ensures email address is not already in use.
        """
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Tällä sähköpostilla on jo tili.")
        return email

