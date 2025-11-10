# oraw_app/forms.py
from __future__ import annotations

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator, validate_email
from django.conf import settings


# ============================================================================
# IOFXML upload form / IOFXML-latauslomake
# ============================================================================
class IOFXMLForm(forms.Form):
    """
    FI: IOF XML 3.0/3.1 ResultList -tiedoston latauslomake. Tekee kevyen
        validoinnin: koko, tiedostopääte ja sisällön pikatunnistus.
    EN: Upload form for IOF XML 3.0/3.1 ResultList. Performs light validation:
        size, extension and quick content sniffing.
    """

    # FI: Kentän nimi "file" → vastaa views.py ja template-käyttöä
    # EN: Field name "file" → matches usage in views.py and templates
    file = forms.FileField(
        label="IOFXML file",
        help_text="Upload IOF XML 3.0/3.1 ResultList (.xml).",
        validators=[FileExtensionValidator(allowed_extensions=["xml"])],
        widget=forms.ClearableFileInput(attrs={"accept": ".xml,application/xml"}),
    )

    # FI: Maksimikoko (MB) konfiguroitavissa asetuksista, oletus 5 MB.
    # EN: Max size (MB) configurable via settings, default 5 MB.
    MAX_MB = getattr(settings, "IOFXML_MAX_UPLOAD_MB", 5)

    def clean_file(self):
        """
        FI: Perusvalidointi: koko, päätteen osuva tarkistus, sekä nopea
            XML-pikatunnistus (ei korvaa skeemavalidointia).
        EN: Basic validation: size, extension check, plus quick XML sniff
            (does not replace full schema validation).
        """
        f = self.cleaned_data["file"]

        # 1) Size
        max_bytes = int(self.MAX_MB) * 1024 * 1024
        if f.size == 0:
            raise forms.ValidationError("Tiedosto on tyhjä.")
        if f.size > max_bytes:
            raise forms.ValidationError(
                f"Tiedosto on liian suuri (> {self.MAX_MB} MB)."
            )

        # 2) Quick content sniff (ResultList tag)
        head = f.read(2048).decode(errors="ignore")
        f.seek(0)  # IMPORTANT: reset read pointer after peek
        if "<ResultList" not in head and "<resultlist" not in head.lower():
            raise forms.ValidationError(
                "Tiedosto ei vaikuta IOF ResultList -XML:ltä."
            )

        return f


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
