from typing import Literal, Dict, Any

import httpx

from api.cloudflare.base import WorkerInfo


class CloudflareAPI:
    def __init__(self, email, key):
        self.email = email
        self.key = key
        self.api_endpoint = "https://api.cloudflare.com/client/v4/"
        self.headers = {
            "X-Auth-Email": self.email,
            "X-Auth-Key": self.key,
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: Literal["GET", "POST", "PUT"],
        url,
        *,
        headers: Dict[str, str] = None,
        json: Dict[str, Any] = None,
        params: Dict[str, Any] = None,
        data: Any = None,
        timeout: int = 10,
    ) -> dict:
        url = self.api_endpoint + url.removeprefix("/")
        headers = self.headers if headers is None else headers

        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(
                    url, headers=headers, params=params, timeout=timeout
                )
            elif method == "POST":
                response = await client.post(
                    url, headers=headers, json=json, timeout=timeout
                )
            elif method == "PUT":
                response = await client.put(
                    url, headers=headers, data=data, timeout=timeout
                )

        return response.json()

    async def list_accounts(self) -> dict:
        url = "/accounts"
        return await self._request("GET", url)

    async def list_zones(self) -> dict:
        url = "/zones"
        return await self._request("GET", url)

    async def list_filters(self, zone_id) -> dict:
        url = f"/zones/{zone_id}/workers/filters"
        return await self._request("GET", url)

    async def list_workers(self, account_id) -> dict:
        url = f"/accounts/{account_id}/workers/scripts"
        return await self._request("GET", url)

    async def graphql_api(self, account_id, start, end, worker_name) -> WorkerInfo:
        """获取worker数据
        :return dict
        {
          'data': {
            'viewer': {
              'accounts': [
                {
                  'workersInvocationsAdaptive': [
                    {
                      'sum': {
                        '__typename': 'AccountWorkersInvocationsAdaptiveSum',
                        'duration': 6195.5075318750005,
                        'errors': 2113,
                        'requests': 91946,
                        'responseBodySize': 277975284672,
                        'subrequests': 166371
                      }
                    }
                  ]
                }
              ]
            }
          },
          'errors': None
        }
        """
        url = "/graphql"
        query = """
query getBillingMetrics($accountTag: string, $datetimeStart: string, $datetimeEnd: string, $scriptName: string) {
    viewer {
      accounts(filter: {accountTag: $accountTag}) {
        workersInvocationsAdaptive(limit: 10, filter: {
          scriptName: $scriptName,
          date_geq: $datetimeStart,
          date_leq: $datetimeEnd
        }) {
          sum {
          duration
          requests
          subrequests
          responseBodySize
          errors
          __typename
        }
        }
      }
    }
  }
"""
        variables = {
            "accountTag": account_id,
            "datetimeStart": start,
            "datetimeEnd": end,
            "scriptName": worker_name,
        }

        result = await self._request(
            "POST", url, json={"query": query, "variables": variables}
        )
        return WorkerInfo.from_dict(result)
