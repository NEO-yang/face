[options]
is_upgrade = False
admin_passwd = admin
db_host = yangxingcai13_db
db_port = 5432
db_user = odoo 
db_password = I2iKYzd1qYWU7d7Oyxc
limit_time_real = 3000

# 使用redis生成最大编码
redis_code_rule_enable = True
redis_host = 192.168.34.101
redis_port = 6379
redis_password = 123456
redis_db = 1
redis_db_robot = 15
redis_max_conn = 100
redis_type = single

# 根据addons_path进行修改配置
base_src_dir = /opt/odoo
addons_path = /opt/odoo/core/addons,/opt/odoo/core/odoo/addons,/opt/odoo/sys,/opt/odoo/platform,/opt/odoo/fin,/opt/odoo/scm,/opt/odoo/ma,/opt/odoo/third-party/OCA-connector,/opt/odoo/third-party/OCA-queue,/opt/odoo/cost,/opt/odoo/qm,/opt/odoo/tax
check_roles = True
load_odoo_module_menu = False
# 新建用户默认密码
default_user_pwd = Abc123456

# log_level = info
# logfile = /opt/odoo/config/log.log

# 创建时数据批量 insert 每次执行条数
# execute_values_size = 1000

# 开发环境 development 生产环境 production
# ps_env = production
# 开发为 developer 实施为 implementer，默认为 developer，这里只影响同步 IDE 和发布的按钮
# ps_role = developer
# 工作流服务地址
ps_flowable_base_url = http://192.168.34.101:8080
# odoo应用服务地址，用于工作流回调odoo服务
ps_odoo_base_url = https://xxx-13.app.mypscloud.com
# websocket地址
# 用于浏览器中通过js连接服务器
ps_socket_base_url = wss://xxx-robot.app.mypscloud.com:7001/wss/
# odoo移动端应用服务地址，用于移动端发送消息
ps_mobile_base_url = http://odoo.studio.insuite.cn

# 网络锁服务地址
ps_netcontrol_url = http://192.168.34.101:8081/odoo

server_wide_modules = web,queue_job,ps_studio,ps_websocket
;xmlrpc_port = 8070
# 运维管理平台服务地址
operation_maintenance_url = https://xxx-upgrade.app.mypscloud.com

# 伙伴插件代码路径
default_partner_code_path = /opt/odoo/partner
# 伙伴插件包的总模块名称，对应 default_partner_code_path 的最后一截
partner_package_name = partner
# 伙伴名称，默认没有数据
# partner_name = hcm

# ba服务地址
# SaaS环境下url和url2两个参数为空，通过代理转发请求ba/bi服务
# op环境下url和url2两个参数需要配置指定的服务地址
url = https://demo-ba.insuite.net
url2 = https://demo-ba.insuite.net
insuite = insuite.net
password = 
http = https://

[queue_job]
channels = root:8,root.seq_generator:1,root.post_account_balance:1,root.post_cash_flow:1,root.update_voucher_state:1,root.lot_seq_generator:1,root.update_card_and_policy_balance:1,root.planning_operation:1,root.fa_depr_wizard:1
scheme = http
host = localhost
;port = 8070
http_auth_user = jobrunner
http_auth_password = s3cr3t
jobrunner_db_host = yangxingcai13_db
jobrunner_db_port = 5432
jobrunner_db_dbfilter = meta,flowable

[rate_center]
# 即期汇率数据仓库参数
database=spot_exchange_rate
username = admin
password = Wvt7GpVOzVCi8pRk
url = currency-rate.svc.insuite.cn
port=8069

# rabbitmq配置参数
[rabbitmq]
# is_rabbitmq参数为True时，通过--load ps_rabbitmq可以随odoo服务启动消费者监听
is_rabbitmq = False
host = 192.168.107.31
port = 5672
virtual_host = /
user_name = inSuite
user_pwd = inSuite2020
# mq_channels参数需要根据需求进行配置修改，key为队列名，value为消费函数名
mq_channels = {"channel1":"search","channel2":"browse"}

# 天气组件配置参数
[weather]
access_key = ck2TXRMF3IU1WaVcq4Hj5RGOHi7FB97u
wearher_app_id = 97658445
weather_app_key = oji9Yec9

# websocket配置参数
# 用于程序中创建客户端连接服务端
[websocket]
ws_host = 127.0.0.1
ws_port = 7001

# ufile存储文件
[oss-ufile]
oss_ufile_enable = False
#账户公钥
ufile_public_key = TOKEN_3a0903be-3e5a-4cb5-9b58-ee7ac2f63cee
#账户私钥
ufile_private_key = 8b00b805-678f-4507-8c4d-59787ff0393d
#空间名称
ufile_bucket = hermes-test
# 上传文件域名
uploadsuffix = .infile.inspurcloud.cn
# 下载文件域名
downloadsuffix = .infile.inspurcloud.cn

# [bank_enterprice_interface]
# crt_file_path = /opt/odoo/config/root.crt
# pem_file_path = /opt/odoo/config/client.pem
# p12_file_path = /opt/odoo/config/client.p12
# p12_file_pwd = aaaaaa
# url_address = https://bic.lc:8080/api/rest
# url_headers = {'Content-Type': 'text/xml;charset=UTF-8'}
# host = 117.73.3.158
# port = 22
# username = admin
# password = odoo
# tenant_id = Default
# sys_id = inSuite