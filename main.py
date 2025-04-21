import asyncio
import random
import yaml
from enums import TaskTypeEnum
from logger import reg_logger
from task import Task


class ActivityEngine:
    logger = reg_logger('[bold yellow]\[ENGINE][/bold yellow]')

    def __init__(self, config_path="config.yml"):
        self.config_path = config_path
        self.active_imagine_tasks = 0
        self.task_queue = asyncio.Queue()
        self.semaphore = asyncio.Semaphore(self.max_tasks)

    @property
    def config(self) -> dict:
        with open(self.config_path) as f:
            config = yaml.safe_load(f)
            return config

    @property
    def max_tasks(self) -> int:
        return self.config["max_tasks"]

    @property
    def consumers(self) -> int:
        return self.config["consumers"]

    def randomize_use_buttons(self) -> int:
        rnge: list[int] = self.config['task']['use_buttons_range']
        return random.randrange(rnge[0], rnge[1])

    async def run(self):
        self.logger.info("[bold cyan]Engine starting")

        consumers = [asyncio.create_task(self.consumer()) for _ in range(self.consumers)]
        consumers.append(asyncio.create_task(self.producer()))
        await asyncio.gather(*consumers)

    async def producer(self):
        self.logger.info("[bold cyan]Producer starting")

        while True:
            if self.active_imagine_tasks >= self.max_tasks:
                await asyncio.sleep(1)
                continue

            create_tasks = self.max_tasks - self.active_imagine_tasks
            self.logger.info(f"[yellow]Queue not full. Creating {create_tasks} tasks")

            for _ in range(create_tasks):
                new_task = Task(task_type="Imagine")
                self.active_imagine_tasks += 1
                await self.task_queue.put(new_task)

            self.logger.info(f"[bold green]Created {create_tasks} tasks")

    async def consumer(self):
        while True:
            task = await self.task_queue.get()
            await self.watch_task(task)
            self.task_queue.task_done()

    async def watch_task(self, task: Task):
        try:
            async with self.semaphore:
                self.logger.info("[cyan]Watching task")

                async with task as imagine:
                    imagine: Task
                    imagine_response: dict = await imagine.start_polling()
                    self.logger.info("[bold green]Imagine finished. Moving queue")
                    self.active_imagine_tasks -= 1

                    self.logger.info("[cyan]Proceeding to button actions")
                    actions_available = imagine_response.get('task_result', {}).get('actions')
                    if not actions_available:
                        self.logger.error(f"[bold red]Task {imagine.task_id} error! No actions available!")
                        return

                    actions_available = [TaskTypeEnum.from_goapi_action(i) for i in actions_available]
                    self.logger.info(f"Available actions: {actions_available}")

                    selected = []
                    use_buttons = self.randomize_use_buttons()
                    self.logger.info(f"Using {use_buttons} buttons")
                    for _ in range(use_buttons):
                        rnd = random.choice(actions_available)
                        actions_available.pop(actions_available.index(rnd))
                        selected.append(rnd)

                    self.logger.info(f"Selected actions: {[i.value for i in selected]}")
                    await imagine.complete_actions(do_actions=selected)

                self.logger.info("Chain completed")
        except Exception as ce:
            self.logger.exception("[bold red]Global chain exception!")


async def main():
    engine = ActivityEngine()

    # Blocking main thread
    await engine.run()


asyncio.run(main())
