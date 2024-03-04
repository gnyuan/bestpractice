Nexus配置常见的外部仓库，用于加速CI等场景。

## 1 pypi仓库
```
1.1 配置仓库 https://mirrors.aliyun.com/pypi/
1.2 后面可用命令 pip install -i http://192.168.0.79:8081/repository/pypi-proxy/simple/ --trusted-host 192.168.0.79 lxml 
1.3 也可以设置仓库
    pip config --user set global.index-url http://192.168.0.79:8081/repository/pypi-proxy/simple/
    pip config --user set global.trusted-host 192.168.0.79:8081
```

## 2 npm仓库
```
2.1 配置仓库 https://registry.npmjs.org/
2.2 后面可用命令 npm --registry http://192.168.0.79:8081/repository/npm-proxy/ install lodash-es vue-cli
2.3 可设置本地仓库 npm config set registry http://192.168.0.79:8081/repository/npm-proxy/
```

## 3 yum仓库
```
3.1 配置yum-proxy, 仓库地址 http://mirrors.aliyun.com/centos/
3.2 配置yum-hosted, Repodata Depth填0， Allow Redeploy.
3.3 配置yum-epel-proxy, 仓库地址 http://mirrors.aliyun.com/epel
3.4 配置yum-group, 把以上三个都加上
3.5 创建yum配置文件`/etc/yum.repos.d/myrepo.repo`其内容是
`
[base]
name=CentOS-$releasever - Base - mirrors.aliyun.com
failovermethod=priority
baseurl=http://192.168.0.79:8081/repository/yum-group/$releasever/os/$basearch/
        http://192.168.0.79:8081/repository/yum-group/$releasever/os/$basearch/
        http://192.168.0.79:8081/repository/yum-group/$releasever/os/$basearch/
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-CentOS-7
 
#released updates 
[updates]
name=CentOS-$releasever - Updates - mirrors.aliyun.com
failovermethod=priority
baseurl=http://192.168.0.79:8081/repository/yum-group/$releasever/updates/$basearch/
        http://192.168.0.79:8081/repository/yum-group/$releasever/updates/$basearch/
        http://192.168.0.79:8081/repository/yum-group/$releasever/updates/$basearch/
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-CentOS-7
 
#additional packages that may be useful
[extras]
name=CentOS-$releasever - Extras - mirrors.aliyun.com
failovermethod=priority
baseurl=http://192.168.0.79:8081/repository/yum-group/$releasever/extras/$basearch/
        http://192.168.0.79:8081/repository/yum-group/$releasever/extras/$basearch/
        http://192.168.0.79:8081/repository/yum-group/$releasever/extras/$basearch/
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-CentOS-7
 
#additional packages that extend functionality of existing packages
[centosplus]
name=CentOS-$releasever - Plus - mirrors.aliyun.com
failovermethod=priority
baseurl=http://192.168.0.79:8081/repository/yum-group/$releasever/centosplus/$basearch/
        http://192.168.0.79:8081/repository/yum-group/$releasever/centosplus/$basearch/
        http://192.168.0.79:8081/repository/yum-group/$releasever/centosplus/$basearch/
gpgcheck=1
enabled=0
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-CentOS-7
 
#contrib - packages by Centos Users
[contrib]
name=CentOS-$releasever - Contrib - mirrors.aliyun.com
failovermethod=priority
baseurl=http://192.168.0.79:8081/repository/yum-group/$releasever/contrib/$basearch/
        http://192.168.0.79:8081/repository/yum-group/$releasever/contrib/$basearch/
        http://192.168.0.79:8081/repository/yum-group/$releasever/contrib/$basearch/
gpgcheck=1
enabled=0
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-CentOS-7
`注意要覆盖原有的yum配置
3.6 创建yum配置文件`/etc/yum.repos.d/epel.repo`其内容是
`
[epel]
name=Extra Packages for Enterprise Linux 7 - $basearch
baseurl=http://192.168.0.79:8081/repository/yum-group/7/$basearch
failovermethod=priority
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-EPEL-7

[epel-debuginfo]
name=Extra Packages for Enterprise Linux 7 - $basearch - Debug
baseurl=http://192.168.0.79:8081/repository/yum-group/7/$basearch/debug
failovermethod=priority
enabled=0
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-EPEL-7
gpgcheck=1

[epel-source]
name=Extra Packages for Enterprise Linux 7 - $basearch - Source
baseurl=http://192.168.0.79:8081/repository/yum-group/7/SRPMS
failovermethod=priority
enabled=0
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-EPEL-7
gpgcheck=1
`
3.7 执行 `yum clean all` `yum makecache`
3.8 后面可用命令 yum -y install python3
```

## 4 apt仓库
```
4.1 配置仓库，分为ubuntu或者debian。而发现版注意是bullseye或者bionic
仓库地址填`https://mirrors.aliyun.com/debian/`  发行版服务端一般是`bullseye`
4.2 配置安全仓库， 仓库地址  `https://mirrors.aliyun.com/debian-security/` 
4.3 登入进入，在目录下`/etc/apt/source.list`执行 
`
sed -i 's/deb.debian.org\/debian/192.168.0.79:8081\/repository\/apt-proxy\//g' /etc/apt/sources.list
sed -i 's|security.debian.org/debian-security|192.168.0.79:8081/repository/apt-security-proxy/|g' /etc/apt/sources.list
`
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
4.4 apt update
4.5 apt install -y python3 telnet vim git
4.6 准备了内网ubuntu的直接配置`
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
```
6.1 配置docker-proxy仓库，地址用`https://registry-1.docker.io/`，选择允许DockerHub
6.2 创建docker-group，HTTP端口勾选并填上28443，勾选允许匿名拉以及使用V1接口与仓库交互，把刚才的docker-proxy加入到组中，保存。这里需要注意，nexus除了暴露8081，也要暴露28443端口。
6.3 docker client端的配置。修改/etc/docker/daemon.json加入proxy地址
`
{"registry-mirrors":[
"http://192.168.0.79:28443",
"https://mirror.ccs.tencentyun.com",
"https://hub-mirror.c.163.com"
],
"insecure-registries": ["10.17.0.122:31535", "192.168.0.79:28443"]
}
`
6.4 重置配置及重启
sudo systemctl daemon-reload
sudo systemctl restart docker
6.5 使用 docker info 查看
```