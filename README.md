# Telegram-Alist bot

主要功能：

- [x] 搜索
    - [x] 文件基本信息
    - [x] 自定义结果数量
    - [x] 文件直链
- [x] 存储
	- [x] 查看存储
    - [x] 启用停用存储
    - [x] 复制存储
    - [ ] 添加存储
    - [ ] 批量添加存储
- [ ] tg文件离线下载到alist
- [x] 备份配置文件到tg
- [ ] 其他功能还没想好

**[@ybyx_bot](http://t.me/ybyx_bot)**

**预览图:**

<details>
<summary><b>搜索</b></summary>

![搜索预览图](https://i.328888.xyz/2023/03/11/soMAw.gif)

</details>

<details>
<summary><b>查看配置</b></summary>

![查看配置](https://i.328888.xyz/2023/03/14/9ccqZ.png)

</details>

<details>
<summary><b>启用/禁用 存储</b></summary>

![管理存储](https://i.328888.xyz/2023/03/11/ssyA5.png)

</details>



<details>
<summary><b>配置备份</b></summary>

![配置备份](https://i.328888.xyz/2023/03/13/9V2FL.png)

</details>



<details>
<summary><b>复制存储</b></summary>

自动复制存储为负载均衡，存储排序会自动加1，自动添加存储备注  
`.balance` 后面的数字为当前时间，  
![复制存储](https://i.328888.xyz/2023/03/14/9cAMV.gif)![复制存储](https://i.328888.xyz/2023/03/14/9c08w.png)

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
bot_api: "" ##bot的key，用 @BotFather 获取
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
cf - 查看当前配置
s - 搜索
sl - 设置搜索结果数量
zl - 开启/关闭 直链
vs - 启用/停用 存储
cs - 复制存储
bc - 备份Alist配置
```


/s + 文件名 进行搜索  

管理员命令：  
/cf 查看当前配置  
/sl + 数字 设置搜索结果数量  
/zl + 1/0 开启/关闭 发送直链  
/vs 启用/停用 存储  
/cs 复制存储  
/bc 备份Alist配置  
