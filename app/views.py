import hashlib
import os
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django import forms
import os
import ai
from django.urls import reverse


class UploadFileForm(forms.Form):
    file = forms.FileField()


# Create your views here.


def handle_uploaded_file(f):
    md5_hash = hashlib.md5()
    for chunk in f.chunks():
        md5_hash.update(chunk)
    hash_name = md5_hash.hexdigest()
    hash_file = hash_name + ".pdf"

    # Create the "uploads" folder if it doesn't exist
    if not os.path.exists("uploads"):
        os.makedirs("uploads")

    file_path = os.path.join("uploads", hash_file)

    if not os.path.exists(file_path):
        with open(file_path, "wb+") as destination:
            for chunk in f.chunks():
                destination.write(chunk)

    return hash_name


def analyze(request):
    file_hash = request.GET.get("file")
    if file_hash is None:
        return HttpResponseRedirect("/")
    thread_id = ai.create_thread(file_hash)
    cpt_codes = ai.prompt_cpt_codes(thread_id)
    conservative_treatment = ai.prompt_conservative_treatment(thread_id)
    guidelines = ai.prompt_guidelines(thread_id)
    return render(
        request,
        "analyze.html",
        {
            "file": file_hash,
            "thread": thread_id,
            "cpt_codes": cpt_codes,
            "conservative_treatment": conservative_treatment,
            "guidelines": guidelines,
        },
    )


def home(request):
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES["file"]
            file_hash = handle_uploaded_file(file)
            return HttpResponseRedirect("/analyze" + "?file=" + file_hash)
    else:
        form = UploadFileForm()
    return render(request, "home.html", {"form": form})
