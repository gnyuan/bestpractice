Nexus配置常见的外部仓库，用于加速CI等场景。

## 1 pypi仓库
```
1.1 配置仓库 https://mirrors.aliyun.com/pypi/
1.2 后面可用命令 pip install -i http://192.168.3.27:8081/repository/proxy-pypi/simple/ --trusted-host 192.168.3.27 lxml 
```

## 2 npm仓库
```
2.1 配置仓库 https://registry.npmjs.org/
2.2 后面可用命令 npm --registry http://192.168.3.27:8081/repository/proxy-npm/ install lodash-es vue-cli
```

## 3 yum仓库
```
2.1 配置仓库 https://registry.npmjs.org/
2.2 后面可用命令 npm --registry http://192.168.3.27:8081/repository/proxy-npm/ install lodash-es vue-cli
```

## 4 apt仓库

## 5 maven仓库

## 6 docker仓库
