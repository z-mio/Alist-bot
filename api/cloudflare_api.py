# -*- coding: UTF-8 -*-
import httpx


# 获取账户信息
async def list_accounts(email, key):
    url = 'https://api.cloudflare.com/client/v4/accounts'
    header = {
        'X-Auth-Email': email,
        'X-Auth-Key': key
    }
    async with httpx.AsyncClient() as client:
        return await client.get(url, headers=header, timeout=10)


# 获取域名信息
async def list_zones(email, key):
    url = 'https://api.cloudflare.com/client/v4/zones'
    header = {
        'X-Auth-Email': email,
        'X-Auth-Key': key
    }
    async with httpx.AsyncClient() as client:
        return await client.get(url, headers=header, timeout=10)


# 获取Workers路由（获取节点域名
async def list_filters(email, key, zone_id):
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/workers/filters"
    headers = {
        'X-Auth-Email': email,
        'X-Auth-Key': key,
    }
    async with httpx.AsyncClient() as client:
        return await client.get(url, headers=headers)


# GraphQL分析API

# 域名数据统计
def graphql_api(email, key, zone_tag, start, end):
    url = 'https://api.cloudflare.com/client/v4/graphql'
    query = """
    {
      viewer {
          zones(filter: { zoneTag: $tag }) {
            httpRequests1dGroups(
              orderBy: [date_ASC]
              limit: 1000
              filter: { date_gt: $start, date_lt: $end }
            ) {
              date: dimensions {
                date
              }
              sum {
                bytes
                requests
              }
            }
          }
        }
      }
    """
    # bytes：使用的流量
    # requests：Bundled请求数
    variables = {
        "tag": zone_tag,
        "start": start,
        "end": end
    }
    header = {
        'X-Auth-Email': email,
        'X-Auth-Key': key,
    }
    return httpx.post(url, headers=header, json={'query': query, 'variables': variables}, timeout=10)
