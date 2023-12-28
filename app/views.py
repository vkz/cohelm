import hashlib
import os
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django import forms
import os
from django.urls import reverse


class UploadFileForm(forms.Form):
    file = forms.FileField()


# Create your views here.


def handle_uploaded_file(f):
    md5_hash = hashlib.md5()
    for chunk in f.chunks():
        md5_hash.update(chunk)
    hash_name = md5_hash.hexdigest() + ".pdf"

    # Create the "uploads" folder if it doesn't exist
    if not os.path.exists("uploads"):
        os.makedirs("uploads")

    with open(os.path.join("uploads", hash_name), "wb+") as destination:
        for chunk in f.chunks():
            destination.write(chunk)
    return hash_name


def home(request):
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES["file"]
            file_hash = handle_uploaded_file(file)
            return HttpResponseRedirect("/" + "?file=" + file_hash)
    else:
        form = UploadFileForm()
    return render(request, "home.html", {"form": form})
