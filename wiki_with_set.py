import asyncio
import re
import sys

import aiohttp
from bs4 import BeautifulSoup


async def get_links(session, page):
    '''
    Функция, возвращающая все ссылки, находящиеся на странице page.

    :param session: Cессия aiohttp.Client
    :param page: Страница, которую необходимо распарсить.
    :return: Возвращает список ссылок на странице page, которые не начинаются с цифр (исключает страницы на даты), не
    содержат в адресе слова (wikipedia, wikidata, wikimedia) и которые соодержат wiki в своем адресе.
    '''
    async with session.get(page) as response:
        text = await response.text()
    soup = BeautifulSoup(text, "html.parser")
    links = set()
    for link in soup.find_all("a", {"href": re.compile("\/wiki\/[\\w]+")}):
        if "wikipedia" not in link["href"] and "wikidata" not in link["href"] \
                and "wikimedia" not in link["href"] and not re.match("\/wiki\/\d+_", link["href"]):
            if link["href"] != page:
                links.add('https://ru.wikipedia.org' + link["href"])
    return links


async def get_backlinks(session, end_page, checked_pages, backlinks):
    '''
    Рекурсивная функция, которая возвращает словарь обратных ссылок (ключ - страница, значение - страница
    с которой возможен переход по ссылке на страницу, указанную в ключе).

    :param session: Cессия aiohttp.Client
    :param end_page: Конечная страница поиска
    :param checked_pages: Проверенные страницы.
    :param backlinks: Словарь обратных ссылок.
    :return: Словарь обратных ссылок (ключ - страница, значение - страница с которой возможен переход по ссылке на
    страницу, указанную в ключе)
    '''

    if end_page in checked_pages or not checked_pages:
        return backlinks

    new_checked_pages = set()

    for checked_page in checked_pages:
        linked_pages = await get_links(session, checked_page)

        for linked_page in linked_pages:
            backlinks[linked_page] = backlinks.get(linked_page, checked_page)
            new_checked_pages.add(linked_page)

    checked_pages = new_checked_pages

    return await get_backlinks(session, end_page, checked_pages, backlinks)


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
        backlinks = await get_backlinks(session, end_page, {start_page, }, dict())

        current_page, bridge = end_page, [end_page]

        while current_page != start_page:
            current_page = backlinks.get(current_page)
            bridge.append(current_page)

        bridge = bridge[::-1]

        for i in range(len(bridge) - 1):
            print(bridge[i])
            link = bridge[i+1]
            sentence = await find_sentence_with_link(session, bridge[i], link.split('org')[-1])
            if sentence:
                print(sentence)

        print(bridge[-1])


if __name__ == '__main__':
    start_page = sys.argv[1]
    end_page = sys.argv[2]
    asyncio.run(build_bridge(start_page, end_page))
