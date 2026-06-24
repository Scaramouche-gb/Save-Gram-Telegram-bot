import asyncio
import os
import random
import glob
from typing import Optional
from yt_dlp import YoutubeDL
from core.config import config
import logging

logger = logging.getLogger(__name__)

class YDLService:
    def __init__(self):
        # Basic settings for all services
        self.base_opts = {
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'restrictfilenames': True,
            'max_filesize': 200 * 1024 * 1024,  # limit 200MB
            'verbose': True, # Add verbose logging for yt-dlp
        }
        self.queue = asyncio.Queue()
        self.proxies = self._load_proxies()
        
    def _load_proxies(self):
        try:
            if os.path.exists("data/proxies.txt"):
                with open("data/proxies.txt", "r") as f:
                    return [line.strip() for line in f if line.strip()]
        except Exception as e:
            logger.error(f"Error loading proxies: {e}")
        return []

    def get_random_proxy(self):
        return random.choice(self.proxies) if self.proxies else None

    def get_random_cookie(self, platform: str):
        # Platform could be 'tiktok', 'instagram', 'youtube', 'pinterest'
        cookie_dir = f"data/cookies/{platform}"
        if os.path.exists(cookie_dir):
            cookies = glob.glob(os.path.join(cookie_dir, "*.txt"))
            if cookies:
                return random.choice(cookies)
        return None

    async def worker(self):
        logger.info("YDL Worker started!")
        while True:
            future, url, extra_opts, platform = await self.queue.get()
            try:
                # Add delay to avoid immediate ban
                await asyncio.sleep(1)
                
                ydl_opts = self.base_opts.copy()
                file_path_template = os.path.join(config.DOWNLOADS_DIR, "%(title)s.%(ext)s")
                ydl_opts['outtmpl'] = file_path_template
                if extra_opts:
                    ydl_opts.update(extra_opts)
                    
                # Add proxy
                proxy = self.get_random_proxy()
                if proxy:
                    ydl_opts['proxy'] = proxy
                
                # Add cookie
                if platform:
                    cookie = self.get_random_cookie(platform)
                    if cookie:
                        ydl_opts['cookiefile'] = cookie
                
                logger.info(f"Downloading {url} | Platform: {platform} | Proxy: {proxy} | Cookie: {ydl_opts.get('cookiefile')}")
                
                result = await asyncio.to_thread(self._sync_download, url, ydl_opts)
                if not future.done():
                    future.set_result(result)
            except Exception as e:
                logger.error(f"Ошибка скачивания в воркере: {e}", exc_info=True)
                if not future.done():
                    future.set_result(None) # don't throw, just return None
            finally:
                self.queue.task_done()

    async def download_video(self, url: str, extra_opts: dict = None, platform: str = None) -> Optional[str]:
        """
        A universal download method.
        Returns the file path or None if an error occurs..
        """
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        await self.queue.put((future, url, extra_opts, platform))
        return await future

    def _sync_download(self, url: str, opts: dict) -> str:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # yt-dlp 2023.01.06 and later will return info['filepath']
            # which is the path to the final processed file.
            return info.get('filepath') or ydl.prepare_filename(info)

# Create one instance of the service for use in the bot
ydl_service = YDLService()
