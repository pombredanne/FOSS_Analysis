from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.template.loader import get_template
from django.template import RequestContext
from django.views.decorators.csrf import ensure_csrf_cookie
import requests
import forms
import re
import json
import helpers.analyzer as analyzer
from helpers.githubAPI import GithubProject as GithubProject
from multiprocessing import Process, Manager
from git import Repo
import os.path
import models

# VIEWS
@ensure_csrf_cookie
def main(request):
    if request.method == 'GET':
        template = get_template("index.html")
        urlForm = forms.urlForm()

        context = {
            'main': True,
            'urlForm': urlForm
        }

        analyzer.loadIndexes()

        return HttpResponse(template.render(context, request))

def analyze(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        url = data['url']
        project = GithubProject(url)

        #Store project
        models.Project.objects.get_or_create(name = project.repo)
        dbProject = models.Project.objects.get(name = project.repo)

        #Store contributors
        contributors = project.getContributors()
        for contributor in contributors:
            models.Contributor.objects.get_or_create(login = contributor['login'],
                                                    email = contributor['email'],
                                                    defaults = {
                                                        'name': contributor['name'],
                                                        'type': contributor['type']
                                                    })
            dbContrib = models.Contributor.objects.get(login = contributor['login'])
            if contributor['login'] == project.user:
                dbProject.owner = dbContrib
                dbProject.save()
            else:
                dbProject.contributors.add(dbContrib)

        #Clone project
        localDir = '/tmp/FOSS_Analysis'
        repoDir = localDir + '/' + project.user + '/' + project.repo
        if not os.path.exists(repoDir):
            Repo.clone_from(url, repoDir)

        #Analyze project
        repo = Repo(repoDir)
        scans = analyzer.scanFolder(repo, repoDir)
        new_json = {
            'owner': project.user,
            'url': url,
            'num_files': len(scans),
            'files': {}
        }

        #Store project contents
        for path, scan in scans.items():
            new_json['files'][path] = scan
            models.File.objects.get_or_create(path = path,
                                            defaults = {'language': scan['language'],
                                                        'project': dbProject})
            dbFile = models.File.objects.get(path = path)
            for copyright in scan['copyrights']:
                models.Copyright.objects.get_or_create(name = copyright[0])
                dbCopyright = models.Copyright.objects.get(name = copyright[0])
                dbFile.copyrights.add(dbCopyright)
            for license in scan['licenses']:
                models.License.objects.get_or_create(name = license['short_name'],
                                                    owner = license['owner'])
                dbLicense = models.License.objects.get(name = license['short_name'])
                dbFile.licenses.add(dbLicense)
            for author in scan['authors']:
                try:
                    dbAuthor = models.Contributor.objects.get(email = scan['authors'][author]['email'])
                except models.Contributor.DoesNotExist:
                    try:
                        dbAuthor = models.Contributor.objects.get(login = author)
                    except models.Contributor.DoesNotExist:
                        try:
                            dbAuthor = models.Contributor.objects.get(name__contains = author)
                        except models.Contributor.DoesNotExist:
                            continue

                models.Blame.objects.get_or_create(file = dbFile,
                                                author = dbAuthor,
                                                defaults = {'lines': scan['authors'][author]['lines']})

        return HttpResponse(json.dumps(new_json))
