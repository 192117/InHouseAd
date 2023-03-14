import asyncio
import re
import sys

import aiohttp
from bs4 import BeautifulSoup


async def fetch_page(session, page):
    '''
    Функция для получения содержимого страницы page.

    :param session: Cессия aiohttp.Client
    :param page: Страница, которую необходимо распарсить.
    :return: Возвращает страницу в виде страницы.
    '''

    async with session.get(page) as response:
        return await response.text()


async def get_links(session, page):
    '''
    Функция, возвращающая все ссылки, находящиеся на странице page.

    :param session: Cессия aiohttp.Client
    :param page: Страница, которую необходимо распарсить.
    :return: Возвращает список ссылок на странице page, которые не начинаются с цифр (исключает страницы на даты), не
    содержат в адресе слова (wikipedia, wikidata, wikimedia) и которые соодержат wiki в своем адресе.
    '''

    response = await fetch_page(session, page)
    soup = BeautifulSoup(response, "html.parser")
    links = set()
    for link in soup.find_all("a", {"href": re.compile("\/wiki\/[\\w]+")}):
        if "wikipedia" not in link["href"] and "wikidata" not in link["href"] \
                and "wikimedia" not in link["href"] and not re.match("\/wiki\/\d+_", link["href"]):
            if link["href"] != page:
                links.add('https://ru.wikipedia.org' + link["href"])
    return links


async def find_sentence_with_link(session, page, link):
    '''
    Функция, возвращающая предложение на странице page, которое содержит ссылку на следующие страницу link.

    :param session: Cессия aiohttp.Client
    :param page: Страница, на которой необходимо найти ссылку на link и текст, где она содержится.
    :param link: Следующая в переходе страница.
    :return: Возвращает предложение, где содержится следующая ссылка или None
    '''

    async with session.get(page) as response:
        text = await response.text()
    soup = BeautifulSoup(text, "html.parser")
    for url in soup.find_all("a", {"href": re.compile("\/wiki\/[\\w]+")}):
        if url['href'] == link:
            return url.parent.text.strip()
    return None


async def build_bridge(start_page, end_page):
    '''
    Функция, печатает стартовую страницу, текст (который содержит ссылку на следующую статью) и ссылку. Так до конечной
    страницы.

    :param start_page: Стартовая страница поиска.
    :param end_page: Конечная страница поиска.
    :return:
    '''

    async with aiohttp.ClientSession() as session:
        async def bsf(start_url):
            answer = dict()
            visited = []
            queue = []
            queue.append(start_url)
            while queue:
                url = queue.pop(0)
                links = await get_links(session, url)
                answer[url] = links
                if end_page in links:
                    visited.append(url)
                    break
                for link in links:
                    if link not in visited:
                        queue.append(link)
                visited.append(url)
            return answer

        result = await bsf(start_page)

        def search(data):
            answer1 = []
            page = end_page
            while page != start_page:
                for key in data:
                    if page in data[key]:
                        answer1.append(key)
                        page = key
                        break
            return answer1[::-1]

        data_list = search(result)
        data_list.append(end_page)

        for i in range(len(data_list) - 1):
            print(data_list[i])
            link = data_list[i + 1]
            sentence = await find_sentence_with_link(session, data_list[i], link.split('org')[-1])
            if sentence:
                print(sentence)

        print(data_list[-1])


if __name__ == '__main__':
    start_page = sys.argv[1]
    end_page = sys.argv[2]
    asyncio.run(build_bridge(start_page, end_page))
