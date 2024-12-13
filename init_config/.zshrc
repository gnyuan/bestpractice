# omzsh中这个PS1很舒服。能显示ip 所在目录 所在分支
show_eth0_ip() {
    local ip=$(ifconfig ens192 | grep 'inet ' | awk '{print $2}')
    local git_branch=$(git branch 2>/dev/null | grep -e ^\* | cut -d ' ' -f2)
    local git_prompt=""
    if [ -n "$git_branch" ]; then
        git_prompt="%F{red}$git_branch%f%F{reset}"
    fi
    PS1="%B%F{green}[${ip}]%F{reset}%F{yellow}%~(%F{reset}${git_prompt}%F{yellow})%F{reset}%B %# "
}

show_eth0_ip
precmd() {
    show_eth0_ip
}

export M2_HOME=/opt/apache-maven-3.9.6
export M2=$M2_HOME/bin
export PATH=$M2:$PATH
