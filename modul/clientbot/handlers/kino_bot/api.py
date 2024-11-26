import ssl

import aiohttp
from aiohttp import TCPConnector

from modul.clientbot.handlers.kino_bot.config import *


async def film_search(q: str) -> dict:
    q = q.lower()
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://{FILMS_API_STORAGE_DOMAIN}/list?token={FILMS_API_KEY}&name={q}', ssl=ssl_context) as response:
            data = await response.json()

    results = {
        'results_count': data['total'],
        'results': [{"id": film['id'], "name": film['name'], "year": film['year']} for film in data['results']]
    }

    return results


async def get_film_poster(id: int) -> dict:
    connector = TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get(
                f'https://{FILMS_API_STORAGE_DOMAIN}/franchise/details?token={FILMS_API_KEY}&id={id}') as response:
            data = await response.json()

    try:
        results = {
            'poster': data['poster'],
            'year': data['year'],
            'name': data['name'],
            'genres': ", ".join([value for key, value in data['genre'].items()]),
            'country': ", ".join([value for key, value in data['country'].items()]),
            'description': data['description']
        }

    except:

        results = {
            'poster': data['poster'],
            'year': data['year'],
            'name': data['name'],
            'genres': "",
            'country': "",
            'description': data['description']
        }

    return results


async def get_film_for_view(id: int) -> dict:
    data = await get_film_poster(id)

    results = {
        "view_link": f'https://api.strvid.ws/embed/movie/{id}?host={FILMS_API_DOMAIN}',
        "poster": data['poster'],
        "name": data['name'],
        'year': data['year'],
        'genres': data['genres'],
        'country': data['country'],
        'description': data['description']
    }

    return results
