from django.shortcuts import render
from .models import Text

# Create your views here.
def home(request):
    posts = Text.objects.all()
    return render(request, 'oraw_app/home.html', {"posts":posts})