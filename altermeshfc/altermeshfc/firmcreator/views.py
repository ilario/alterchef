# -*- coding: utf-8 -*-

import os
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse_lazy
from django.views.generic import ListView, UpdateView, DetailView, CreateView, DeleteView

from utils import LoginRequiredMixin
from models import IncludeFiles, Network, FwProfile, FwJob
from forms import IncludeFilesFormset, IncludePackagesForm, FwProfileForm, \
                   NetworkForm, FwProfileSimpleForm, CookFirmwareForm


def index(request):
    return render(request, "firmcreator/index.html", {
    })

##
# Network Views

class NetworkCreateView(CreateView, LoginRequiredMixin):
    model = Network

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super(NetworkCreateView, self).form_valid(form)

class NetworkUpdateView(UpdateView, LoginRequiredMixin):
    model = Network
    def get_object(self, queryset=None):
        object = super(NetworkUpdateView, self).get_object(queryset)
        if object.user == self.request.user:
            return object
        else:
            raise Http404

class NetworkDeleteView(DeleteView, LoginRequiredMixin):
    model = Network
    success_url = reverse_lazy('network-list')

    def get_object(self, queryset=None):
        object = super(NetworkDeleteView, self).get_object(queryset)
        if object.user == self.request.user:
            return object
        else:
            raise Http404

class NetworkDetailView(DetailView):
    model = Network

class NetworkListView(ListView):
    model = Network

##
# Profile Views

class FwProfileDetailView(DetailView):
    model = FwProfile

def create_profile_simple(request):

    if request.method == "POST":
        form = FwProfileSimpleForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():

            based_on = form.cleaned_data.get("based_on")
            fw_profile = form.save()
            return redirect("fwprofile-detail", slug=fw_profile.slug)
    else:
        form = FwProfileSimpleForm(user=request.user)

    return render(request, "firmcreator/create_profile_simple.html", {
        'form': form,
    })

@login_required
def crud_profile_advanced(request, slug=None):
    instance = get_object_or_404(FwProfile, slug=slug) if slug else None
    if request.method == "POST":
        profile_form = FwProfileForm(request.POST, user=request.user, instance=instance)
        include_files_formset = IncludeFilesFormset(request.POST, prefix="include-files")
        include_packages_form = IncludePackagesForm(request.POST)
        if profile_form.is_valid() and include_files_formset.is_valid and \
           include_packages_form.is_valid():
            fw_profile = profile_form.save(user=request.user)
            fw_profile.include_packages = include_packages_form.to_str()
            files = {}
            for f in include_files_formset.cleaned_data:
                files[f["name"]] = f["content"]
            fw_profile.include_files = files
            fw_profile.save()
            return redirect("fwprofile-detail", slug=fw_profile.slug)

    else:
        based_on = request.GET.get("based_on", None)
        if based_on:
            based_on = get_object_or_404(FwProfile, pk=based_on)

        def get_initial_files(obj):
            return [{"name":name, "content": content} for name, content in obj.include_files.iteritems()]

        inherited = instance or based_on
        initial_files = get_initial_files(inherited) if inherited else None
        include_files_formset = IncludeFilesFormset(initial=initial_files, prefix="include-files")
        include_packages_form = IncludePackagesForm.from_str(inherited.include_packages if inherited else "")

        profile_form = FwProfileForm(request.GET or None, instance=instance, user=request.user)

    return render(request, "firmcreator/crud_profile.html", {
        'include_files_formset': include_files_formset,
        'include_packages_form': include_packages_form,
        'profile_form': profile_form,
        'object': instance,
    })


def serialize_job():
    return {}

@login_required
def cook(request, slug):
    profile = get_object_or_404(FwProfile, slug=slug)

    context = {"profile": profile}
    jobs = FwJob.objects.filter(profile=profile, status__in=["WAITING", "STARTED"])
    if jobs:
        context["job"] = jobs[0]
    else:
        if request.method == "POST":
            form = CookFirmwareForm(request.POST)
            if form.is_valid():
                # TODO:
                # Retrieve data from profile, network and form and create a suitable
                # job
                job_data = serialize_job()
                job = FwJob.objects.create(status="WAITING", profile=profile,
                                           user=request.user, job_data=job_data)
                return redirect("fwprofile-detail", slug=profile.slug)
        else:
            form = CookFirmwareForm()
        context["form"] = form

    return render(request, "firmcreator/cook.html", context)
