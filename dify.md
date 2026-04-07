
Dify 服务器 (xjp-dify)
公网 IP：143.198.82.67
内网 IP (VPC)：10.104.0.3 (dify)
管理系统/MySQL 服务器 (xjp-mb)
公网 IP：139.59.231.126
内网 IP (VPC)：10.104.0.6 (我们这台服务器)


结合你的真实 IP，你的实操步骤如下：
场景 1：管理系统 (xjp-mb) 要调用 Dify 的 API
为了让管理系统通过内网高速请求 https://dify.mysolo.codes/，你需要去管理系统服务器 (xjp-mb) 上修改 hosts：
在 xjp-mb 终端输入：nano /etc/hosts
在文件最下面加上这行代码（把域名强行指向 Dify 的内网 IP）：
code
Text
10.104.0.3  dify.mysolo.codes
保存退出。以后这台机器请求这个域名，就会自动走内网。


<iframe
 src="https://dify.mysolo.codes/chatbot/VvvBNdRfN7wc0oAm"
 style="width: 100%; height: 100%; min-height: 700px"
 frameborder="0"
 allow="microphone">
</iframe>