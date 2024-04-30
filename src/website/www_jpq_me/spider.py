import re
import json
import asyncio
import aiofiles
import aiohttp

from aiohttp import ClientSession, ClientTimeout, TCPConnector
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from os import path, makedirs, remove
from typing import List

from util_libs.color import blue_txt, red_txt, green_txt


class Parser:
    _config: None | dict[str, any]
    _current_dir: str
    _config_file_path: str
    _headers: dict[str, any]
    _session: ClientSession | None = None
    _download_dir: str

    def __init__(self) -> None:
        self._current_dir = path.dirname(path.abspath(__file__))
        self._config_file_path = path.join(self._current_dir, "config.json")
        self._headers = {"User-Agent": UserAgent().random}

        with open(self._config_file_path, "r") as file:
            # 读取配置文件
            self._config = json.load(file)

        self._download_dir = self._config.get("download_dir")

    async def fetch_page(self, url: str, **keyword: any):
        async with self._session.get(url, headers=self._headers, **keyword) as response:
            if response.status == 200:
                return await response.content.read()
            else:
                print("请求错误，响应状态码：{}".format(response.status))
                return None

    # 开始解析
    async def start_parse(self):
        base_url = self._config.get("site_url")
        concurrent = int(self._config.get("concurrent"))
        timeout = int(self._config.get("timeout"))

        # session 配置
        client_timeout = ClientTimeout(total=timeout)
        tcp_connector = TCPConnector(limit=concurrent)

        async with ClientSession(timeout=client_timeout, connector=tcp_connector) as session:
            self._session = session
            content = await self.fetch_page(base_url)

            if content is None:
                return

            soup = BeautifulSoup(content, "html.parser")
            links = soup.find_all("a", string=["视频", "漫画"])

            for link in links:
                url = link.attrs.get("href") if "href" in link.attrs else None
                type = link.string

                if url is None:
                    continue

                if type == "视频":
                    await self.parse_video(url)
                    pass
                elif type == "漫画":
                    pass

    async def parse_video(self, url: str):
        content = await self.fetch_page(url)
        video_origin: str = self._config.get("video_origin")
        allow_resolution: List[str] = self._config.get("allow_resolution")
        requests: List[any] = []

        if content:
            soup = BeautifulSoup(content, "html.parser")
            imgs = soup.find_all("img", attrs={"class": re.compile(r"img-responsive")})

            for img in imgs:
                # 视频列表页面的入口链接
                list_entry = img.find_parent("a")

                if list_entry is None:
                    continue

                href = list_entry.attrs.get("href")
                # 资源的文件夹名称
                folder_name: str = list_entry.attrs.get("title")
                list_page = await self.fetch_page(href)

                if list_page is None:
                    continue

                list_soup = BeautifulSoup(list_page, "html.parser")
                list = list_soup.find_all(
                    "li", attrs={"class": re.compile(r"wp-manga-chapter")}
                )

                for item in list:
                    # 视频播放的入口链接
                    video_entry = item.find("a")
                    video_entry_href = video_entry.attrs.get("href")
                    # 文集爱名称
                    file_name = video_entry.string.strip()

                    play_page = await self.fetch_page(video_entry_href)

                    if play_page is None:
                        continue

                    play_soup = BeautifulSoup(play_page, "html.parser")
                    sources: List[str] = play_soup.find_all(
                        "source", attrs={"src": re.compile(video_origin)}
                    )

                    # 是否已匹配到
                    is_match = False

                    for resolution in allow_resolution:
                        if is_match:
                            break

                        for source in sources:
                            video_url = source.attrs.get("src")
                            match_index = source.find(resolution)

                            if match_index != -1:
                                is_match = True
                                requests.append(
                                    self.download_video(
                                        video_url, folder_name, file_name + ".mp4"
                                    )
                                )
                                break

        await asyncio.gather(*requests)

        print(green_txt("所有视频已成功下载!"))

    async def download_video(self, url: str, folder_name: str, file_name: str):
        # 格式化文件名称,去除不合规符号
        for char in r'\/:*?"<>|':
            file_name = file_name.replace(char, "_")

        folder_path = path.join(self._download_dir, folder_name)
        file_path = path.join(folder_path, file_name)

        if path.exists(file_path):
            return None

        makedirs(folder_path, exist_ok=True)
        await self.download(url, file_path)

    async def download(self, url: str, file_path: str, retry=0):
        try:
            remove(file_path)
        except FileNotFoundError:
            pass
        finally:
            try:
                if retry > 3:
                    print(red_txt("已3次下载失败，即将终止下载：") + file_path)
                    async with aiofiles.open(file_path + '.fail', 'w') as file:
                        await file.write("")
                    return

                # 设置请求过期时间
                t = int(self._config.get("timeout"))
                timeout = ClientTimeout(total=retry * t * 5 + t)

                async with self._session.get(url, headers=self._headers, timeout=timeout) as response:
                    if response.status == 200:
                        async with aiofiles.open(file_path, "wb") as f:
                            print(blue_txt("{}下载：".format("开始" if not retry else "第{}次重新".format(retry))) + file_path)
                            async for chunk in response.content.iter_any():
                                await f.write(chunk)
                    else:
                        print(red_txt("请求失败：") + "{}，响应状态码--{}".format(url, response.status))
            except (aiohttp.ClientPayloadError, asyncio.TimeoutError):
                print(red_txt("下载失败：") + "{}，即将重试！".format(file_path))
                await self.download(url, file_path, retry + 1)
