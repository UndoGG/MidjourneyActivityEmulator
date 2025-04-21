import asyncio
import json
import os

import aiohttp
import yaml
from aiohttp import ClientSession
from dotenv import load_dotenv

from enums import TaskStatusEnum
from logger import reg_logger


class GoAPI:
    logger = reg_logger('[bold magenta]\[GoAPI][/bold magenta]')
    def __init__(self, config_path='config.yml'):
        self.config_path = config_path
        self.headers = {
            "X-API-KEY": self.token
        }

    @property
    def config(self) -> dict:
        with open(self.config_path) as f:
            config = yaml.safe_load(f)
            return config['goapi']

    @property
    def process_mode(self) -> str:
        return self.config['process_mode']

    @property
    def timeout(self):
        return self.config['http_timeout_seconds']

    @property
    def token(self) -> str:
        load_dotenv()
        return os.environ.get('GOAPI_TOKEN')

    async def retry_timeout(self, retries: int = 3, *args, **kwargs):
        try:
            resp = await self.request(**kwargs)

            if retries != 3:
                self.logger.info(f"[green]Succeeded after {3 - retries} retries")

            return resp
        except asyncio.TimeoutError as e:
            self.logger.warning(f"Timeouted. Retrying {retries - 1} more times")
            if retries < 1:
                raise e
            return await self.retry_timeout(retries - 1, **kwargs)

    async def request(self, url, payload: dict = None, method='GET', **kwargs) -> tuple[dict, int]:
        """
        Request url

        :param url: Full request url
        :param payload: Optional data (auto json converted)
        :param method: HTTP method ('get', 'post', 'put', 'delete', etc)
        :raises ClientResponseError If status is not 200
        :returns: Tuple of [response_json, status]
        """
        method = method.upper()
        parsed_args = {}
        if payload:
            parsed_args['data'] = json.dumps(payload)

        self.logger.debug(f"[bold cyan]Requesting {method} {url} with payload [cyan]{payload}[/cyan]")

        async with ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
            async with session.request(method, url, headers=self.headers, timeout=self.timeout, **parsed_args, **kwargs) as response:
                response_json = None
                try:
                    response_json = await response.json()
                except Exception:
                    self.logger.error("[bold red]JSON decode failed"
                                      f"\nContent: {response.content}"
                                      f"\nStatus code: {response.status}")

                log = self.logger.debug
                if not (300 > response.status >= 200):
                    log = self.logger.error
                log(f"Response {response.status} JSON: [cyan]{response_json}")

                response.raise_for_status()

                return [response_json, response.status]

    async def fetch(self, task_id: str) -> tuple[str, dict]:
        """
        Fetch task progress

        :param task_id: Task id to fetch
        :raises ClientResponseError If status is not 200
        :returns: Tuple of [TaskStatusEnum, goapi_response_json]
        """

        url = self.config['urls']['fetch']
        payload = {
            "task_id": task_id
        }
        response_json, _ = await self.retry_timeout(url=url, method='POST', payload=payload)

        status = response_json['status']
        return TaskStatusEnum.from_goapi_status(status), response_json

    async def imagine(self, prompt: str, ar: str) -> tuple[str, dict]:
        """
        Create /imagine

        :param prompt: Prompt
        :param ar: Aspect ratio
        :raises ClientResponseError If status is not 200
        :returns: Tuple of [new_task_id, goapi_response_json]
        """
        url = self.config['urls']['imagine']
        payload = {
            "prompt": prompt,
            "aspect_ratio": ar,
            "process_mode": self.process_mode,
            "webhook_endpoint": "",
            "webhook_secret": ""
        }

        response_json, _ = await self.request(url, payload=payload, method='post')
        return response_json.get('task_id', None), response_json

