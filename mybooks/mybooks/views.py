from django.shortcuts import render, redirect
from django.http import HttpResponse
from allauth.socialaccount.models import SocialLogin, SocialToken, SocialApp, SocialAccount
from allauth.socialaccount.forms import DisconnectForm
import requests
import urllib.request
import json

def home_page(request):
    return render(request, 'home_page.html')

def search_simple(request):
    return render(request, 'search_simple.html')

def search_form(request):
    return render(request, 'search_form.html')

def search(request):
    errors = []
    if request.GET:
        url = ('https://www.googleapis.com/books/v1/volumes?q=')

        # simple search getting results
        if 'query' in request.GET:
            if not request.GET['query']:
                errors.append('Please enter a search term')
            else:
                query = request.GET['query']
                query = query.replace(' ', '%20')
                url += str(query)
                with urllib.request.urlopen(url) as url:
                    parsed_json = json.loads(url.read().decode())
                    if parsed_json['totalItems'] == 0:
                        errors.append('No results found: Please enter a different search.')
            if not errors:
                return render(request, 'search_results.html', {'parsed_json': parsed_json})
            else:
                return render(request, 'search_simple.html', {'errors': errors})
        
        # search form getting results
        else:
            if not request.GET['title_search'] and not request.GET['author_search'] and not request.GET['genre_search'] and not request.GET['isbn_search']:
                errors.append('Must enter at least one keyword')
            else:
                if request.GET['title_search']:
                    title_search = request.GET['title_search']
                    title_search = title_search.replace(' ', '%20')
                    url += 'intitle:' + str(title_search)
                if request.GET['author_search']:
                    author_search = request.GET['author_search']
                    author_search = author_search.replace(' ', '%20')
                    if url != 'https://www.googleapis.com/books/v1/volumes?q=':
                        url += '+'
                    url += 'inauthor:' + str(author_search)
                if request.GET['genre_search']:
                    genre_search = request.GET['genre_search']
                    genre_search = genre_search.replace(' ', '%20')
                    if url != 'https://www.googleapis.com/books/v1/volumes?q=':
                        url += '+'
                    url += 'subject:' + str(genre_search)
                    
# ISBN search not working - per google
#                if request.GET['isbn_search']:
#                    isbn_search = request.GET['isbn_search']
#                    isbn_search = isbn_search.replace(' ', '')
#                    if url != 'https://www.googleapis.com/books/v1/volumes?q=':
#                        url += '+'
#                    url += 'isbn:' + str(isbn_search)

                if request.GET['filter']:
                    filter_search = request.GET['filter']
                    url += '&filter=' + str(filter_search)
                if request.GET['orderBy']:
                    orderBy = request.GET['orderBy']
                    url += '&orderBy=' + str(orderBy)
                if request.GET['printType']:
                    printType = request.GET['printType']
                    url += '&printType=' + str(printType)
                if request.GET['maxResults']:
                    results_search = request.GET['maxResults']
                    url += '&maxResults=' + str(results_search)
                with urllib.request.urlopen(url) as url:
                    parsed_json = json.loads(url.read().decode())
                    if parsed_json['totalItems'] == 0:
                        errors.append('No results found: Please enter a different search.')
            if not errors:
                return render(request, 'search_results.html', {'parsed_json': parsed_json})
    return render(request, 'search_form.html', {'errors': errors})

def book_info(request):
    bookshelf_json = ''
    message = []
    book_info = request.GET['book_info']
    if request.user.is_authenticated:
        user = request.user
        access_token = str(SocialToken.objects.get(account__user=request.user, account__provider='google'))

        # allows bookshelf changes if authenticated
        if 'bookshelf_id' in request.GET:
            bookshelf_id = request.GET['bookshelf_id']
            if 'add' in request.GET['action_type']:
                post_url = 'https://www.googleapis.com/books/v1/mylibrary/bookshelves/' + str(bookshelf_id) + '/addVolume?volumeId=' + str(book_info)
                querystring = {'volumeId': str(book_info)}
                headers = {'Authorization': 'Bearer %s' % access_token}
                response = requests.request('POST', post_url, headers=headers, params=querystring)
                message.append('Book Successfully Added!')
            elif 'remove' in request.GET['action_type']:
                post_url = 'https://www.googleapis.com/books/v1/mylibrary/bookshelves/' + str(bookshelf_id) + '/removeVolume?volumeId=' + str(book_info)
                querystring = {'volumeId': str(book_info)}
                headers = {'Authorization': 'Bearer %s' % access_token}
                response = requests.request('POST', post_url, headers=headers, params=querystring)
                message.append('Book Successfully Removed!')

        # gets bookshelf list if authenticated
        bookshelf_list = 'https://www.googleapis.com/books/v1/mylibrary/bookshelves?access_token=' + str(access_token)
        with urllib.request.urlopen(bookshelf_list) as url:
            bookshelf_json = json.loads(url.read().decode())
        bookshelf_json['items'] = sorted(bookshelf_json['items'], key=lambda k: k['id'], reverse=True)

    url = 'https://www.googleapis.com/books/v1/volumes/' + str(book_info)
    with urllib.request.urlopen(url) as url:
        parsed_json = json.loads(url.read().decode())
    parsed_json['volumeInfo']['title'] += (':' if 'subtitle' in parsed_json['volumeInfo'] else '')
    if 'medium' not in parsed_json['volumeInfo']['imageLinks']:
        parsed_json['volumeInfo']['imageLinks']['medium'] = (parsed_json['volumeInfo']['imageLinks']['thumbnail']) 
    return render(request, 'book_info_results.html', {'parsed_json': parsed_json, 'bookshelf_json': bookshelf_json, 'message': message})

def my_account(request):
    user = request.user
    access_token = str(SocialToken.objects.get(account__user=request.user, account__provider='google')) 

    # gets bookhelf list if authenticated
    bookshelf_list = 'https://www.googleapis.com/books/v1/mylibrary/bookshelves?access_token=' + str(access_token)
    with urllib.request.urlopen(bookshelf_list) as url:
        bookshelf_json = json.loads(url.read().decode())
    bookshelf_json['items'] = sorted(bookshelf_json['items'], key=lambda k: k['id'], reverse=True)

    for kind in bookshelf_json['items']:
        if 0 == kind['volumeCount']:
            kind['volumeCount'] = ''

    return render(request, 'my_account.html', {'bookshelf_json': bookshelf_json})

def bookshelf_volumes(request):
    url = request.GET['self_link']
    with urllib.request.urlopen(url) as response:
        parsed_json = json.loads(response.read().decode())
    return render(request, 'search_results.html', {'parsed_json': parsed_json})