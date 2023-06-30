# verdaccio配置
该镜像含以下功能：
* 1 自建npm源，用以支持CI/CD
* 2 在下载时如果本地没有，则缓存淘宝源，但初次下载有时有点问题，需要手工重试。
* 3 npm install package-name --registry=MY_URL