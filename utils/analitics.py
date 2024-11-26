from dataclasses import dataclass
from typing import List
from uuid import uuid4

from utils.img_analitic.main import ImageAnalitics, ImageAnaliticsColumnInfo, ImageAnaliticsConfig, ImageAnaliticsData, \
    ImageAnaliticsDateRange, ImageAnaliticsGraph, ImageAnaliticsSimpleData


@dataclass
class AnaliticData:
    title: str
    dates: List[str]
    values: List[float]


@dataclass
class AnaliticInfoData:
    title: str
    data: List[ImageAnaliticsDateRange] | List[ImageAnaliticsSimpleData]


def make_analitic_graph(bot_username: str, datas: List[AnaliticData]):
    img = ImageAnalitics(800, 800, f'@{bot_username}', ImageAnaliticsConfig('utils/img_analitic/BOOKOS.TTF',
                                                                            'utils/img_analitic/background_image.png'))
    for data in datas:
        img.add_row(
            data.title,
            ImageAnaliticsColumnInfo([
                ImageAnaliticsData(
                    data.title,
                    ImageAnaliticsGraph(
                        data.title,
                        'Дата',
                        'Количество',
                        data.dates,
                        data.values
                    )
                )
            ])
        )
    return img.gen()


def make_analitic(bot_username: str, datas: List[List[AnaliticInfoData]]):
    img = ImageAnalitics(800, 800, f'@{bot_username}', ImageAnaliticsConfig('utils/img_analitic/BOOKOS.TTF',
                                                                            'utils/img_analitic/background_image.png'))
    for data in datas:
        row = []
        for it in data:
            row.append(ImageAnaliticsData(
                it.title,
                it.data
            ))
        img.add_row(
            f'{uuid4()}',
            ImageAnaliticsColumnInfo(row)
        )
    return img.gen()


def gen_data(datas, attr_name, funct: callable = None):
    data = {}
    for new_client in datas:
        arrt_value = getattr(new_client, attr_name)
        if funct:
            arrt_value = funct(arrt_value)
        if arrt_value in data:
            data[arrt_value] += 1
        else:
            data[arrt_value] = 1
    return data
