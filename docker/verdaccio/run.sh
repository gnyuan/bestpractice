# 首次需要配置config文件夹下的config.yaml
docker run -d \
  --restart always \
  --name verdaccio \
  -p 4873:4873 \
  -v /root/verdaccio/config:/verdaccio/conf:rw \
  -v /root/verdaccio/storage:/verdaccio/storage:rw \
  verdaccio/verdaccio:5.25
