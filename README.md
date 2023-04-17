# Telegram-Alist bot
**Alist项目地址：**
[![Readme Card](https://github-readme-stats.vercel.app/api/pin/?username=alist-org&repo=alist)](https://github.com/alist-org/alist)  

**主要功能：**

- [x] 搜索
    - [x] 文件基本信息
    - [x] 自定义结果数量
    - [x] 文件直链
- [x] 存储
    - [x] 开关存储
    - [x] 删除存储
    - [x] 复制存储
    - [x] 新建存储
    - [x] 批量新建存储
- [x] Alist配置备份&定时备份
- [ ] tg文件转存
- [ ] tg频道订阅

### 预览图:

<details>
<summary><b>搜索</b></summary>

和alist搜索方式一样  

![搜索预览图](https://i.328888.xyz/2023/03/11/soMAw.gif)

</details>


<details>
<summary><b>查看配置</b></summary>

![查看配置](https://i.328888.xyz/2023/03/21/TO6PN.png)

</details>


<details>
<summary><b>配置备份</b></summary>

可以回复消息来添加备注，可以重复修改

![配置备份](https://i.328888.xyz/2023/04/04/ibJg73.gif)

</details>


<details>
<summary><b>存储管理菜单</b></summary>

![管理存储](https://i.328888.xyz/2023/03/21/TOQ43.png)

</details>


<details>
<summary><b>开关存储</b></summary>

![管理存储](https://i.328888.xyz/2023/03/21/TbfTH.gif)

</details>


<details>
<summary><b>复制存储</b></summary>

自动复制存储为负载均衡，存储排序会自动加1，自动添加存储备注  
`.balance` 后面的数字为当前时间，  
![复制存储](https://i.328888.xyz/2023/03/14/9c08w.png)![复制存储](https://i.328888.xyz/2023/03/14/9cAMV.gif)

</details>


<details>
<summary><b>删除存储</b></summary>

![复制存储](https://i.328888.xyz/2023/03/21/TbwTo.gif)

</details>


<details>
<summary><b>新建&批量新建</b></summary>

可以设置默认配置，新建存储会优先使用默认配置。所有参数都可以设置默认值

比如设置了PikPak的`用户名`和`密码`，新建的时候就不需要输入了，只需要输入`挂载路径`和`分享ID`  

![默认配置](https://i.328888.xyz/2023/04/11/iBDWVv.png)![默认配置](https://i.328888.xyz/2023/04/11/iBDjRQ.png)

### 新建存储：

![新建&批量新建](https://i.328888.xyz/2023/03/21/TjH68.png)![新建&批量新建](https://i.328888.xyz/2023/03/21/TjkUU.gif)

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
bot:
  proxy_url: #不填为不使用代理，支持http/https代理，例：http://127.0.0.1:7890
user:
  admin: #管理员用户id,可以添加多个，可通过@get_id_bot获取id
    - 123456789
    - 456789456
  alist_host: "http://127.0.0.1:5244" #alist ip:port
  alsit_token: "" #alist token
  bot_token: ""  # bot的api token，从 @BotFather 获取
search:
  alist_web: "https://" #你的alist域名
```

**4.启动bot**

**前台启动bot**

``` 
python3 bot.py
```


**设置开机自启**

以下是一整条命令，一起复制到SSH客户端运行
``` 
cat > /etc/systemd/system/alist-bot.service <<EOF
[Unit]
Description=Alist-bot Service
After=network.target

[Service]
User=root
WorkingDirectory=/root/Alist-bot
ExecStart=nohup python3 bot.py > botlog.log 2>&1 &
Restart=always

[Install]
WantedBy=multi-user.target

EOF
```

然后，执行 `systemctl daemon-reload` 重载配置，现在你可以使用这些命令来管理程序：  


启动：`systemctl start alist-bot`  
停止：`systemctl stop alist-bot`    
开启开机自启：`systemctl enable alist-bot`  
关闭开机自启：`systemctl disable alist-bot`  
重启：`systemctl restart alist-bot`  
状态：`systemctl status alist-bot`  

## 开始使用

私聊或群组里发送指令  
第一次使用可以发送`/menu`自动设置Bot菜单  

**指令列表：**

```
/start 开始
/s + 文件名 进行搜索

管理员命令：
/cf 查看当前配置
/sl+数字 设置搜索结果数量
/zl+1/0 开启/关闭发送直链
/st 存储管理
/bc 备份Alist配置
/sbt 设置定时备份
```



