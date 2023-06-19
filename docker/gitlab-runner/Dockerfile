FROM gitlab/gitlab-runner:latest

# 安装 Docker 客户端
RUN curl -fsSL https://get.docker.com -o get-docker.sh && \
    sh get-docker.sh && \
    usermod -aG docker gitlab-runner
USER root

