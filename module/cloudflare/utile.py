import datetime
from dataclasses import dataclass

import httpx
from httpx import AsyncClient
from loguru import logger

from api.cloudflare.base import WorkerInfo
from api.cloudflare.cloudflare_api import CloudflareAPI
from config.config import CloudFlareInfo
from tools.utils import pybyte


@dataclass
class NodeStatus:
    url: str
    status: int


# 检查节点状态
async def check_node_status(url: str, cli: AsyncClient = None) -> NodeStatus:
    status_code_map = {
        200: [url, 200],
        429: [url, 429],
    }
    try:
        if cli:
            response = await cli.get(f"https://{url}")
        else:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"https://{url}")
    except httpx.ConnectError:
        return NodeStatus(url, 502)
    finally:
        logger.info(f"节点: {url}|状态码: {response.status_code}")
    return NodeStatus(*status_code_map.get(response.status_code, [url, 502]))


# 将当前日期移位n天，并返回移位日期和移位日期的前一个和下一个日期。
def date_shift(n: int = 0):
    today = datetime.date.today()
    shifted_date = datetime.date.fromordinal(today.toordinal() + n)
    previous_date = datetime.date.fromordinal(shifted_date.toordinal() - 1)
    next_date = datetime.date.fromordinal(shifted_date.toordinal() + 1)
    previous_date_string = previous_date.isoformat()
    next_date_string = next_date.isoformat()
    return shifted_date.isoformat(), previous_date_string, next_date_string


@dataclass
class NodeInfo:
    text: str
    code: int
    worker_info: WorkerInfo


CODE_EMOJI = {
    200: "🟢",
    429: "🔴",
    502: "⭕️",
}


async def get_node_info(day: int, info: CloudFlareInfo) -> NodeInfo:
    """获取节点信息"""
    d = date_shift(day)
    wi = await CloudflareAPI(info.email, info.global_api_key).graphql_api(
        info.account_id, d[0], d[0], info.worker_name
    )
    code = await check_node_status(info.url)

    text = f"""
{info.url} | {CODE_EMOJI.get(code.status)}
请求：<code>{wi.requests}</code> | 带宽：<code>{pybyte(wi.response_body_size)}</code>
———————"""

    return NodeInfo(text, code.status, wi)


def re_remark(remark: str, node: str):
    if "节点：" in remark:
        return "\n".join(
            [f"节点：{node}" if "节点：" in line else line for line in remark.split("\n")]
        )
    return f"节点：{node}\n{remark}"
