# 首次需要初始化，后面就不需要了
# devpi-init && \
docker run -d --name devpi -p 3141:3141 \
--restart always -v ./root:/root:rw python:3.10-slim \
/bin/bash -c "pip install -i https://mirrors.aliyun.com/pypi/simple/ --upgrade pip && \
pip install -q -U devpi-server==6.9.0 supervisor -i https://mirrors.aliyun.com/pypi/simple/  && \
devpi-server --host 0.0.0.0 --port 3141"

