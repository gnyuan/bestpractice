# gitlab-runner配置
构建支持Docker in Docker的gitlab-runner
* 1 使用gitlab-runner
* 2 下载docker
* 3 使用的时候，主要要把/var/run/docker.sock挂载进去，使得本地的docker可以使用宿主机的docker