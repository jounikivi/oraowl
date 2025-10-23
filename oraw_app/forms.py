# oraw_app/forms.py
from __future__ import annotations

from django import forms


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
