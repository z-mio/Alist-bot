FROM ubuntu

ADD . /root/Alist-bot
WORKDIR /root/Alist-bot

RUN apt-get update \
    && apt-get install -y sudo \
    && sudo apt-get install -y python3 python3-pip \
    && pip3 install -r requirements.txt


CMD ["python3", "/root/Alist-bot/bot.py"]
