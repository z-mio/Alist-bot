# Telegram-Alist bot

主要功能：

- [x] 搜索
    - [x] 文件基本信息
    - [x] 自定义结果数量
    - [x] 文件直链
- [x] 存储
	- [x] 查看存储
    - [x] 启用停用存储
    - [ ] 添加存储
    - [ ] 批量添加存储
- [ ] 其他功能还没想好

<details>
<summary><b>预览图</b></summary>

![搜索预览图](https://i.328888.xyz/2023/03/11/soMAw.gif)

![管理存储](https://i.328888.xyz/2023/03/11/ssyA5.png)
</details>

## 安装

**1.安装 python3-pip**

```
apt install python3-pip
```


**2.将项目克隆到本地**
``` 
git clone https://github.com/z-mio/Alist-bot.git && cd Alist-bot && pip3 install -r requirements.txt
```

**3.修改 config.yaml 里的配置信息**

``` 
admin: ##管理员用户id,可以添加多个
  - 123456789
  - 456789456
alist_host: "http://127.0.0.1:5244" ##alist ip:port
alist_web: "https://" ##你的alist域名
alsit_token: "" ##alist token
bot_key: "" ##bot的key，用 @BotFather 获取
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

私聊或群里发送指令

**指令列表：**

```
start - 开始
s - 搜索
sl - 搜索结果数量
zl - 是否开启直链
```

/s + 文件名 进行搜索  
/sl + 数字 设置搜索结果数量（仅管理员可用）  
/zl + 1/0 开启/关闭发送直链（仅管理员可用）  
