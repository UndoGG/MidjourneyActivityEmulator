import asyncio
import random

import yaml

from enums import TaskStatusEnum, TaskTypeEnum
from goapi import GoAPI
from logger import logger, reg_logger


class TaskFailedException(Exception):
    def __init__(self, response: dict):
        self.response = response

    def __str__(self):
        return "Task failed with response: {}".format(self.response)


class Task:
    def __init__(self, config_path='config.yml', task_type: str = "Unknown", existing_task_id=None):
        self.logger = logger
        self.task_id = existing_task_id
        self.task_type = task_type

        if existing_task_id:
            self.logger = reg_logger(f"[bold cyan]\[{existing_task_id} {task_type}][/bold cyan]")

        self.goapi = GoAPI()
        self.config_path = config_path

    @property
    def config(self) -> dict:
        with open(self.config_path) as f:
            config = yaml.safe_load(f)
            return config['task']

    @property
    def ar(self) -> str:
        return self.config['ar']

    def generate_prompt(self) -> str:
        prompt = random.choice(self.config['prompts'])
        if "--ar" in prompt:
            self.logger.warning(
                "[bold yellow]It is highly NOT recommended to use '--ar' in prompts! System will add specified ar automatically!")
        else:
            prompt += f' --ar {self.ar}'

        return prompt

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.logger.info("Closing task...")

        if exc_type:
            self.logger.error('[bold red]Task closed with exception', exc_info=(exc_type, exc_val, exc_tb))

        return self

    async def __aenter__(self):
        if self.task_id:
            raise ValueError("Task already started")

        self.logger.info("[cyan]Starting task...")

        task_id, _ = await self.goapi.imagine(prompt=self.generate_prompt(), ar=self.ar)

        self.logger = reg_logger(f"[bold cyan]\[{task_id} {self.task_type}][/bold cyan]")
        self.task_id = task_id
        self.logger.info("[bold green]Imagine started successfully!")

        return self

    async def start_polling(self):
        """
        Start task polling
        :return: status fetch response, when completed
        :raises TaskFailedException: if task fails
        """
        if not self.task_id:
            raise ValueError("Task not started")

        self.logger.info("[cyan]Waiting for task to complete...")

        while True:
            await asyncio.sleep(1)
            self.logger.debug("Checking task status...")
            status, status_response = await self.goapi.fetch(self.task_id)

            if status == TaskStatusEnum.FAILED:
                self.logger.error(f"[bold red]Task failed! => [cyan]{status_response}")
                raise TaskFailedException(response=status_response)

            if status == TaskStatusEnum.COMPLETED:
                self.logger.info("[bold green]Task completed")
                return status_response

    async def complete_actions(self, do_actions: list[TaskTypeEnum], do_recursive: bool = True) -> None:
        if not self.task_id:
            raise ValueError("Task not ready for completing actions")

        occupied_indexes = {}
        for action in do_actions:
            payload = action.__payload__(origin_task_id=self.task_id, occupied_indexes=occupied_indexes.get(action))
            if not payload:
                continue

            if payload.get('index') and action.is_onetime:
                self.logger.info(f"[yellow]Included {payload['index']} to occupied indexes")
                occupied_indexes.setdefault(action, [])
                occupied_indexes[action].append(payload['index'])

            url = action.__goapi_url__()
            if not url:
                self.logger.error(f"[bold yellow]GoAPI URL not found for {action}")
                continue

            self.logger.info(f"Requesting [yellow]{action}[/yellow] on [cyan]{url}[/cyan] "
                             f"\nwith payload [cyan]{payload}[/cyan]")

            create_task_response, _ = await self.goapi.request(url=url, method='POST', payload=payload)
            if not create_task_response.get('task_id'):
                self.logger.error(f"[bold red]Failed to gather task_id from [cyan]{create_task_response}")
                continue

            task = Task(existing_task_id=create_task_response['task_id'], task_type=action.value.capitalize())

            try:
                finished_task_response = await task.start_polling()
            except TaskFailedException as tf:
                self.logger.error(f"[bold red]Child task uuid={task.task_id} failed!")
                self.logger.error(f"JSON: [cyan]{tf.response}")
                continue

            if not do_recursive:
                self.logger.info(f"[bold green]Child task {task.task_id} ({task.task_type}) finished. Chain completed!")
                return

            self.logger.info(f"[bold green]Child task {task.task_id} finished. Recursively completing actions")

            actions_available = finished_task_response.get('task_result', {}).get('actions')
            if not actions_available:
                self.logger.error(f"[bold red]Task {task.task_id} error! No actions available!. Continuing to next action")
                continue

            actions_available = [TaskTypeEnum.from_goapi_action(i) for i in actions_available]
            actions_available = [i for i in actions_available if i is not None]
            self.logger.info(f"Available actions: {actions_available}")

            selected = []
            use_buttons = self.randomize_use_buttons()
            self.logger.info(f"Using {use_buttons} buttons recursively")
            for _ in range(use_buttons):
                rnd = random.choice(actions_available)
                actions_available.pop(actions_available.index(rnd))
                selected.append(rnd)

            self.logger.info(f"Selected actions: {[i.value for i in selected]}")
            await task.complete_actions(do_actions=selected, do_recursive=False)


    def randomize_use_buttons(self) -> int:
        rnge: list[int] = self.config['use_buttons_range_recursive']
        return random.randrange(rnge[0], rnge[1])

