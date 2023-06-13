docker run -d \
--restart=always \
--privileged \
--name v2raya \
-e V2RAYA_ADDRESS=0.0.0.0:2017 \
-p 2017:2017 \
-p 2018:20170 \
-p 20171:20171 \
-p 20172:20172 \
-v /home/yuangn/v2raya/modules:/lib/modules \
-v /home/yuangn/v2raya/resolv.conf:/etc/resolv.conf \
-v /home/yuangn/v2raya/v2raya:/etc/v2raya \
-v /home/yuangn/v2raya/v2ray:/etc/v2ray \
mzz2017/v2raya
