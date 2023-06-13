FROM centos:7.6.1810
RUN curl -o /etc/yum.repos.d/CentOS-Base.repo http://mirrors.aliyun.com/repo/Centos-7.repo && \
    yum clean all && \
    yum makecache && \
    yum install -y net-tools wget vim git unzip zip tree gcc c++ yum-utils && \
    yum-config-manager --add-repo http://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo && \
    yum install -y docker-ce docker-ce-cli containerd.io

USER root
CMD ["/bin/bash"]
