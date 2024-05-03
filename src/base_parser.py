import aiohttp
import asyncio
import random
import aiofiles

from fake_useragent import UserAgent
from os import path, rename
from utils.color import red_txt, blue_txt, green_txt, orange_txt
from utils.date import datetime_title


class BaseParser:
    # 单位s
    _timeout: int
    _session: aiohttp.ClientSession
    _semaphore: asyncio.Semaphore
    _headers: dict[str, str]
    _count: dict[str, int]

    def __init__(self):
        self._timeout = 300
        self._headers = {"User-Agent": UserAgent().random}
        self._count = {"success": 0, "fail": 0, "request_err": 0}
        self._semaphore = asyncio.Semaphore(30)

    @property
    def success(self) -> int:
        return self._count.get("success")

    @success.setter
    def success(self, val: int):
        self._count.update({"success": val})

    @property
    def fail(self) -> int:
        return self._count.get("fail")

    @fail.setter
    def fail(self, val: int):
        self._count.update({"fail": val})

    @property
    def request_err(self) -> int:
        return self._count.get("request_err")

    @request_err.setter
    def request_err(self, val: int):
        self._count.update({"request_err": val})

    def start(self):
        asyncio.run(self.create_session())

        success_txt = green_txt("成功：{}".format(self.success))
        fail_txt = red_txt("失败：{}".format(self.fail))
        request_err_txt = orange_txt("请求失败：{}".format(self.request_err))

        print(blue_txt(datetime_title("执行完毕")) + success_txt + "，" + fail_txt + "，" + request_err_txt)

    async def create_session(self):
        connector = aiohttp.TCPConnector(limit=50)

        async with aiohttp.ClientSession(connector=connector) as session:
            self._session = session
            await self.crawling()

    async def crawling(self):
        pass

    async def download(self, url: str, save_path: str, retry=0):
        if path.exists(save_path):
            return

        if retry > 2:
            self.fail += 1
            print(red_txt(datetime_title("已3次下载失败，即将终止下载")) + save_path)
            return

        # 下载路径，.part用以标识当前文件正在下载
        download_path = save_path + ".part"

        try:
            async with self._session.head(url, headers=self._headers) as res:
                # 每重试一次增加5倍的原超时时间
                timeout = aiohttp.ClientTimeout(total=retry * self._timeout * 5 + self._timeout)

                if res.status == 200 and res.headers.get("Accept-Ranges"):
                    request_size = res.headers.get("Content-Length")

                    if path.exists(download_path):
                        file_size = path.getsize(download_path)
                        headers = self._headers.copy()
                        headers.update({"Range": "{}-{}".format(file_size + 1, request_size)})

                        async with self._session.get(url, headers=headers, timeout=timeout) as res:
                            if res.status == 200:
                                async with aiofiles.open(download_path, 'ab') as f:
                                    print(blue_txt("[{}下载：".format("开始" if not retry else "第{}次重新]：".format(retry))) + save_path)

                                    async for chunk in res.content.iter_any():
                                        await f.write(chunk)

                                self.success += 1
                                rename(download_path, save_path)
                                print(green_txt(datetime_title("成功下载")) + save_path)
                            else:
                                self.request_err += 1
                                print(orange_txt(datetime_title("请求失败")) + "{}，响应状态码--{}".format(url, res.status))
                    else:
                        await self.full_download(url, save_path, timeout, retry)
                else:
                    await self.full_download(url, save_path, timeout, retry)
        except (aiohttp.ClientPayloadError, asyncio.TimeoutError):
            print(red_txt(datetime_title("下载失败")) + "{}，即将重试！".format(save_path))
            await self.download(url, save_path, retry + 1)

    # 全量下载
    async def full_download(self, url: str, save_path: str, timeout: aiohttp.ClientTimeout, retry=0):
        download_path = save_path + ".part"

        async with self._session.get(url, headers=self._headers, timeout=timeout) as res:
            if res.status == 200:
                async with aiofiles.open(download_path, "wb") as f:
                    print(blue_txt(datetime_title("{}下载".format("开始" if not retry else "第{}次重新".format(retry)))) + save_path)

                    async for chunk in res.content.iter_any():
                        await f.write(chunk)

                self.success += 1
                rename(download_path, save_path)
                print(green_txt(datetime_title("成功下载")) + save_path)
            else:
                self.request_err += 1
                print(orange_txt(datetime_title("请求失败")) + "{}，响应状态码--{}".format(url, res.status))

    # 默认5-15秒的延迟
    async def random_sleep(self, start=5, end=15):
        random_sleep_time = random.uniform(start, end)
        await asyncio.sleep(random_sleep_time)
