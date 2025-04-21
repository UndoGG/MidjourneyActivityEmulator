import random
from enum import Enum
from typing import Union

import yaml

from logger import logger


class TaskStatusEnum(Enum):
    IN_PROGRESS = 'In progress'
    COMPLETED = 'Completed'
    FAILED = 'Failed'

    @classmethod
    def from_goapi_status(cls, status: str) -> 'TaskStatusEnum':
        match status:
            case 'completed':
                return TaskStatusEnum.COMPLETED
            case 'finished':
                return TaskStatusEnum.COMPLETED
            case 'failed':
                return TaskStatusEnum.FAILED
            case 'processing':
                return TaskStatusEnum.IN_PROGRESS
            case 'pending':
                return TaskStatusEnum.IN_PROGRESS
            case 'staged':
                return TaskStatusEnum.IN_PROGRESS
            case 'retry':
                return TaskStatusEnum.FAILED
            case _:
                raise ValueError(f"Unknown GoAPI status {status}")


class TaskTypeEnum(Enum):
    IMAGINE = 'Imagine'
    UPSCALE = 'Upscale'
    VARIATION = 'Variation'
    INPAINT = 'Inpaint'
    PAN = 'Pan'
    REROLL = 'Reroll'
    OUTPAINT = 'Outpaint'

    @property
    def config(self) -> dict:
        with open("config.yml") as f:
            config = yaml.safe_load(f)
            return config


    @property
    def is_onetime(self):
        onetime = [TaskTypeEnum.UPSCALE]
        return self in onetime

    @classmethod
    def from_goapi_task_type(cls, task_type: str):
        match task_type:
            case 'imagine':
                return TaskTypeEnum.IMAGINE
            case 'upscale':
                return TaskTypeEnum.UPSCALE
            case 'variation':
                return TaskTypeEnum.VARIATION
            case 'pan':
                return TaskTypeEnum.PAN
            case 'reroll':
                return TaskTypeEnum.REROLL
            case 'outpaint':
                return TaskTypeEnum.OUTPAINT
            case 'inpaint':
                return TaskTypeEnum.INPAINT



    @classmethod
    def from_goapi_action(cls, action: str) -> Union['TaskTypeEnum', None]:
        if action[-1].isdigit():
            return cls.from_goapi_task_type(action[:-1])
        if '_' not in action:
            return cls.from_goapi_task_type(action)

        parsed_value = action.split('_')
        action_parts = ['variation', 'outpaint', 'pan', 'upscale']


        action, value = None, None
        for part in parsed_value:
            if part in action_parts:
                action = part
            else:
                value = part

        if value in ['high', 'low', 'subtle', 'creative']:
            return None

        return cls.from_goapi_task_type(action)


    def __payload__(self, origin_task_id: str, occupied_indexes: list[int] | None = None) -> dict | None:
        if not occupied_indexes:
            occupied_indexes = []

        available_indexes = ['1', '2', '3', '4']
        available_indexes = [i for i in available_indexes if int(i) not in occupied_indexes]
        if len(available_indexes) < 1:
            logger.warning(f"[yellow]Ran out of available indexes for {self}")
            return None

        task_payload = {
            TaskTypeEnum.IMAGINE: None,
            TaskTypeEnum.INPAINT: None,

            TaskTypeEnum.UPSCALE: {
                "origin_task_id": origin_task_id,
                "index": random.choice(available_indexes)
            },

            TaskTypeEnum.VARIATION: {
                "origin_task_id": origin_task_id,
                "index": random.choice(available_indexes),
                "prompt": "",
                "aspect_ratio": ""
            },

            TaskTypeEnum.OUTPAINT: {
                "origin_task_id": origin_task_id,
                "zoom_ratio": random.choice(["1.5", "1.25", "2.0", "1.75"]),
                "prompt": "",
                "aspect_ratio": ""
            },

            TaskTypeEnum.REROLL: {
                "origin_task_id": origin_task_id,
                "prompt": "",
                "aspect_ratio": ""
            },

            TaskTypeEnum.PAN: {
                "origin_task_id": origin_task_id,
                "direction": random.choice(['up', 'left', 'down', 'right']),
                "prompt": "",
                "aspect_ratio": ""
            },
        }

        general_payload = {
            "webhook_endpoint": "",
            "webhook_secret": "",
        }

        payload = task_payload.get(self)
        if not payload:
            logger.warning(f"Payload not available for task type {self}")
            return None

        return payload | general_payload

    def __goapi_url__(self):
        try:
            return self.config['goapi']['urls'][self.value.lower()]
        except KeyError:
            return None
