import re
import json
import asyncio
import aiohttp

from aiohttp import ClientTimeout, TCPConnector
from bs4 import BeautifulSoup
from os import path, makedirs
from typing import List, Coroutine, Any
from base_parser import BaseParser
from util_libs.color import blue_txt, orange_txt
from util_libs.date import datetime_title


class JPQParser(BaseParser):
    _config: None | dict[str, any]
    _current_dir: str
    _config_file_path: str
    _download_dir: str

    def __init__(self) -> None:
        super().__init__()
        self._current_dir = path.dirname(path.abspath(__file__))
        self._config_file_path = path.join(self._current_dir, "config.json")

        with open(self._config_file_path, "r") as file:
            # 读取配置文件
            self._config = json.load(file)

        self._download_dir = self._config.get("download_dir")

    async def fetch_page(self, url: str, **keyword: any):
        async with self._session.get(url, headers=self._headers, **keyword) as res:
            await self.random_sleep(2, 6)

            if res.status == 200:
                return await res.content.read()
            else:
                print(orange_txt(datetime_title("请求失败")) + "{}，响应状态码--{}".format(url, res.status))
                return None

    async def create_session(self):
        concurrent = int(self._config.get("concurrent"))
        timeout = int(self._config.get("timeout"))

        client_timeout = ClientTimeout(total=timeout)
        tcp_connector = TCPConnector(limit=concurrent)

        async with aiohttp.ClientSession(timeout=client_timeout, connector=tcp_connector) as session:
            self._session = session
            await self.crawling()

    # 开始解析
    async def crawling(self):
        base_url = self._config.get("site_url")
        content = await self.fetch_page(base_url)

        if content is None:
            return

        soup = BeautifulSoup(content, "html.parser")
        links = soup.find_all("a", string=["视频", "漫画"])
        requests: List[Coroutine[Any, Any, None]] = []

        for link in links:
            url = link.attrs.get("href") if "href" in link.attrs else None
            type = link.string

            if url is None:
                continue

            if type == "视频":
                pages = await self.get_pages(url)

                for page in range(1, pages + 1):
                    requests.append(self.parse_video_list("{}{}".format(url, "/page/{}".format(page) if not page == 1 else ""), page))
                pass
            elif type == "漫画":
                pass

        print(blue_txt("{}{}解析开始".format(datetime_title("解析"), base_url)))
        await asyncio.gather(*requests)

    # 获取总页数
    async def get_pages(self, url):
        content = await self.fetch_page(url)

        if content:
            soup = BeautifulSoup(content, "html.parser")
            pagination = soup.find(attrs={"class": "wp-pagenavi", "role": "navigation"})

            if pagination:
                target = pagination.find(attrs={"class": "pages"})
                if target:
                    match = re.search(r"共\s*(\d+)\s*页", target.string)
                    if match:
                        return int(match.group(1))

            return 1
        else:
            return 0

    # 解析视频列表页面
    async def parse_video_list(self, url: str, page: int):
        async with self._semaphore:
            print(blue_txt(datetime_title("解析")) + "正在解析视频分类第{}页，地址：{}".format(page, url))
            content = await self.fetch_page(url)
            requests: List[Coroutine[Any, Any, None]] = []

            if content:
                soup = BeautifulSoup(content, "html.parser")
                imgs = soup.find_all("img", attrs={"class": re.compile(r"img-responsive")})

                for img in imgs:
                    # 视频列表页面的入口链接
                    list_entry = img.find_parent("a")

                    if not list_entry:
                        continue

                    href = list_entry.attrs.get("href")

                    if href == self._config.get("site_url"):
                        continue
                    # # 资源的文件夹名称
                    folder_name: str = list_entry.attrs.get("title")
                    requests.append(self.parse_video_entrance(href, folder_name))

            await asyncio.gather(*requests)

    # 解析视频入口页面
    async def parse_video_entrance(self, url: str, folder_name: str):
        video_origin: str = self._config.get("video_origin")
        allow_resolution: List[str] = self._config.get("allow_resolution")
        entrances_page = await self.fetch_page(url)

        if entrances_page is None:
            return

        entrances_soup = BeautifulSoup(entrances_page, "html.parser")
        entrances = entrances_soup.find_all(
            "li", attrs={"class": re.compile(r"wp-manga-chapter")}
        )

        requests: List[Coroutine[Any, Any, None]] = []

        for entrance in entrances:
            # 视频播放的入口链接
            video_entrance = entrance.find("a")
            video_entrance_href = video_entrance.attrs.get("href")
            # 文件名称
            file_name = video_entrance.string.strip()
            play_page = await self.fetch_page(video_entrance_href)

            if play_page is None:
                return

            play_soup = BeautifulSoup(play_page, "html.parser")
            sources: List[str] = play_soup.find_all(
                "source", attrs={"src": re.compile(video_origin)}
            )

            # 是否已匹配到视频
            isMatch = False

            for resolution in allow_resolution:
                if (isMatch):
                    break

                for source in sources:
                    video_url = source.attrs.get("src")
                    match_index = source.find(resolution)

                    if match_index != -1:
                        isMatch = True
                        requests.append(self.download_video(video_url, folder_name, file_name + ".mp4"))
                        break

        await asyncio.gather(*requests)

    async def download_video(self, url: str, folder_name: str, file_name: str):
        # 格式化文件名称,去除不合规符号
        for char in r'\/:*?"<>|':
            file_name = file_name.replace(char, "_")

        folder_path = path.join(self._download_dir, folder_name)
        file_path = path.join(folder_path, file_name)

        if path.exists(file_path):
            return

        makedirs(folder_path, exist_ok=True)
        await self.download(url, file_path)
