from django.http import HttpResponse



# Create your views here.
def health(request):
    # FI: Yksinkertainen "elossa" -vastaus, jotta URLit toimivat.
    # EN: Simple "alive" response so URLs work.
    return HttpResponse("OK")
