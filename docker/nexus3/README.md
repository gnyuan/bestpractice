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
3.1 配置仓库 http://mirrors.aliyun.com/centos/
3.2 创建yum配置文件`/etc/yum.repos.d/myrepo.repo`其内容是
`
[nexus]
name=Nexus Repository
baseurl=http://192.168.0.79:8081/repository/yum-proxy/$releasever/os/$basearch/
enabled=1
gpgcheck=0
`注意要覆盖原有的yum配置
3.3 执行 `yum clean all` `yum makecache`
3.4 后面可用命令 yum -y install python3
```

## 4 apt仓库
```
4.1 配置仓库，分为ubuntu或者debian。而发现版注意是bullseye或者bionic
仓库地址填`https://mirrors.aliyun.com/debian/`  发行版服务端一般是`bullseye`
4.2 登入进入，在目录下`/etc/apt/source.list`执行 
`sed -i 's/deb.debian.org\/debian/192.168.0.79:8081\/repository\/apt-proxy\//g' /etc/apt/sources.list`
如果要整个文件写入，可以执行`
cat > /etc/apt/sources.list << EOF  
deb https://mirrors.aliyun.com/debian/ bullseye main non-free contrib  
deb-src https://mirrors.aliyun.com/debian/ bullseye main non-free contrib  
deb https://mirrors.aliyun.com/debian-security/ bullseye-security main  
deb-src https://mirrors.aliyun.com/debian-security/ bullseye-security main  
deb https://mirrors.aliyun.com/debian/ bullseye-updates main non-free contrib  
deb-src https://mirrors.aliyun.com/debian/ bullseye-updates main non-free contrib  
deb https://mirrors.aliyun.com/debian/ bullseye-backports main non-free contrib  
deb-src https://mirrors.aliyun.com/debian/ bullseye-backports main non-free contrib  
EOF
`
4.3 apt update
4.4 apt install -y python3 telnet vim git
4.5 准备了内网ubuntu的直接配置`
cat > /etc/apt/sources.list << EOF  
deb http://192.168.0.79:8081/repository/ubuntu-proxy/ jammy main non-free contrib  
deb-src http://192.168.0.79:8081/repository/ubuntu-proxy/ jammy main non-free contrib  
EOF
`
```

## 5 maven仓库
```
5.1 nexus已经配置好了maven，可以直接使用。
5.2 在pom.xml中配置`
<repositories>
        <repository>
            <id>central</id>
            <url>http://192.168.0.79:8081/repository/maven-central/</url>
        </repository>
    </repositories>
`
```

## 6 docker仓库
