

# Telegram-Alist文件搜索机器人

- 可以用来搜索 Alist 里的文件，然后返回 文件名、文件大小、文件链接和文件直链
- 可以自定义搜索结果数量


<details>
<summary><b>预览图</b></summary>

![搜索](https://i.328888.xyz/2023/03/09/onocX.gif)

![更多搜索结果](https://m.360buyimg.com/babel/jfs/t20250308/72563/37/26636/298059/6408b461Fef22bf8c/97378b473d532012.png)
</details>


## 食用方法

**1.安装 python3-pip**

```
apt install python3-pip
```


**2.将项目克隆到本地**
``` 
git clone https://github.com/z-mio/alist-search-tg-bot.git && cd alist-search-tg-bot && pip3 install -r requirements.txt
```

**3.修改 bot.py 里的配置信息**

``` 
alist_host = "http://127.0.0.1:5244"  ## alist ip:port
alist_web = "https://" ## 你的alist域名
alsit_token = "" ## alist token
bot_key = "" ## bot的key，用 @BotFather 获取
per_page = 5 ## 搜索结果返回数量，默认5条
```

**4.启动bot**

前台启动机器人

``` 
python3 bot.py
```

后台启动机器人

``` 
nohup python3 bot.py > botlog.log 2>&1 &
```

## 开始使用

**指令列表：**

- start - 开始
- s - 搜索
- sl - 搜索结果数量
- zl - 是否开启直链

/s + 文件名 进行搜索  
/sl + 数字 设置搜索结果数量（仅管理员可用）  
/zl + 1/0 开启/关闭发送直链（仅管理员可用）  