import asyncio
import random

import httpx
from fastapi import Response
from loguru import logger
from starlette.responses import RedirectResponse, PlainTextResponse, FileResponse

from api.alist.alist_api import alist
from api.alist.base import SettingInfo
from api.alist.base.base import AListAPIResponse
from bot import fast
from config.config import cf_cfg, chat_data, plb_cfg
from module.cloudflare.utile import check_node_status
from tools.scheduler_manager import aps
from tools.utils import encode_url

TEXT_TYPES = []
async_client = httpx.AsyncClient()


@fast.get("/{path:path}")
async def redirect_path(path: str):
    if not plb_cfg.enable:
        return PlainTextResponse("代理负载均衡已关闭", status_code=503)

    path = encode_url(path, False)
    if not path:
        return Response(content="运行中...", media_type="text/plain; charset=utf-8")

    r = await available_nodes()
    if not r:
        return FileResponse(
            path="./module/cloudflare/warning.txt",
            filename="网站的下载节点流量已全部用完 早上8点自动恢复.txt",
        )
    new_url = f"https://{r}/{path}?sign={alist.sign(f'/{path}')}"
    ext = path.split(".")[-1]
    if ext in TEXT_TYPES:
        return await forward_text(new_url)
    return RedirectResponse(url=encode_url(new_url), status_code=302)


def init_node(app):
    # 文本文件不能直接重定向, 需要先获取文件内容再返回
    global TEXT_TYPES
    r: AListAPIResponse[SettingInfo] = app.loop.run_until_complete(
        alist.setting_get("text_types")
    )
    TEXT_TYPES = r.data.value.split(",")
    app.loop.run_until_complete(refresh_nodes_regularly())
    aps.add_job(
        func=refresh_nodes_regularly,
        trigger="interval",
        job_id="returns_the_available_nodes",
        seconds=600,
    )


async def forward_text(new_url):
    """处理文本文件"""
    response = await async_client.get(new_url)
    headers = dict(response.headers)
    headers.pop("content-encoding", None)
    headers.pop("content-length", None)
    return Response(
        content=response.content,
        media_type=headers["content-type"],
        headers=headers,
    )


async def available_nodes():
    """随机获取一个可用节点, 如果一直使用一个节点, 请求量过大时会被限制"""
    if not (node_list := chat_data.get("node_list")):
        return
    return await random_node(node_list)


async def random_node(node_list):
    """随机选择一个节点, 如果节点不可用则重新选择"""
    r = await check_node_status(random.choice(node_list), async_client)
    return r.url if r.status == 200 else await random_node(node_list)


async def refresh_nodes_regularly():
    """刷新可用节点池"""
    # tasks = [get_node_info(i) for i in cf_cfg.nodes]
    # result_list = [
    #     result[0]
    #     for result in await asyncio.gather(*tasks, return_exceptions=True)
    #     if not isinstance(result, BaseException) and result[1] < 100000
    # ]
    tasks = [check_node_status(node.url, async_client) for node in cf_cfg.nodes]
    r = await asyncio.gather(*tasks, return_exceptions=True)
    node_list = []
    for i in r:
        if isinstance(i, BaseException):
            logger.error(f'刷新节点错误: {i}')
            continue
        if i.status == 200:
            node_list.append(i.url)

    chat_data["node_list"] = node_list
    logger.info(f"节点已刷新 | {node_list}")
