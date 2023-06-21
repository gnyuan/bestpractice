export GITLAB_HOME=/root/gitlab
docker run -d \
        -v $GITLAB_HOME/config:/etc/gitlab \
        -v $GITLAB_HOME/logs:/var/log/gitlab \
        -v $GITLAB_HOME/data:/var/opt/gitlab \
        --hostname 192.168.0.79 \
        --env GITLAB_OMNIBUS_CONFIG="external_url 'http://192.168.0.79:1002/'; gitlab_rails['ldap_enabled'] = true; \
gitlab_rails['time_zone'] = 'Asia/Shanghai'; \
gitlab_rails['smtp_enable'] = true; \
gitlab_rails['smtp_address'] = 'xxx'; \
gitlab_rails['smtp_port'] = 587; \
gitlab_rails['smtp_user_name'] = 'xxx'; \
gitlab_rails['smtp_password'] = 'xxx'; \
gitlab_rails['smtp_domain'] = 'xxx'; \
gitlab_rails['smtp_authentication'] = 'login'; \
gitlab_rails['smtp_enable_starttls_auto'] = true; \
gitlab_rails['ldap_servers'] = {
  'main' => {
    'label' => 'LDAP',
    'host' =>  'xxx,
    'port' => 389,
    'uid' => 'sAMAccountName',
    'bind_dn' => 'ccfund\xxx',
    'password' => 'xxx',
    'encryption' => 'plain',
    'verify_certificates' => false,
    'active_directory' => true,
    'allow_username_or_email_login' => true,
    'base' => 'DC=ccfund,DC=com',
  }
};" \
        -p 1001:443 -p 1002:1002 -p 1003:22 \
        -e GITLAB_ROOT_EMAIL="xxx" -e GITLAB_ROOT_PASSWORD="xxx" \
        --shm-size 256m \
        --name gitlab --restart unless-stopped gitlab/gitlab-ce:latest
