export GITLAB_HOME=/home/yuangn/gitlab
docker run -d \
        -v $GITLAB_HOME/config:/etc/gitlab \
        -v $GITLAB_HOME/logs:/var/log/gitlab \
        -v $GITLAB_HOME/data:/var/opt/gitlab \
        --hostname gitlab \
        -p 1001:443 -p 1002:80 -p 1003:22 \
        -e GITLAB_ROOT_EMAIL="xxx@xxx.com" -e GITLAB_ROOT_PASSWORD="xxxx" \
        -e EXTERNAL_URL="http://gitlab" \
        --name gitlab --restart unless-stopped gitlab/gitlab-ce:latest