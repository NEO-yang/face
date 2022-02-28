[options]
is_upgrade = False
admin_passwd = admin
db_host = yangxingcai_db
db_port = 5432
db_user = odoo
db_password = yangxingcaiqsdysBM33oQVKToQ
limit_time_cpu = 6000
limit_time_real = 12000000
limit_memory_hard = 4221225472
limit_memory_soft = 4221225472
# log_level = debug
ps_env = development
create_profile_test_data=False
# logfile = a.log

# 使用redis生成最大编码
redis_code_rule_enable = False
redis_host = 192.168.34.101
redis_port = 6379
redis_password = 123456
redis_db = 1
redis_db_robot = 15
redis_max_conn = 100
redis_type = single

# ba服务地址
url = https://demo-ba.insuite.net
url2 = https://demo-ba.insuite.net
insuite = insuite.net
password = 
http = https://

# 根据addons_path进行修改配置
base_src_dir = /opt/py/odoo
addons_path = /opt/py/odoo/core/addons,/opt/py/odoo/core/odoo/addons,/opt/py/odoo/platform/,/opt/py/odoo/ma,/opt/py/odoo/sys,/opt/py/odoo/fin,/opt/py/odoo/scm,/opt/py/odoo/mfg,/opt/py/odoo/cost,/opt/py/odoo/qm,/opt/py/odoo/tax,/opt/py/odoo/third-party/OCA-connector,/opt/py/odoo/third-party/OCA-queue
ps_module_white_list = ps_hmp,ps_mdm,ps_wkf,ps_hmp,mail,sale,sale_management,sale_coupon,board,ps_admin,ps_post,ps_sample,account,project,mrp,barcodes,ps_web,purchase,ps_gl,scm_base,ps_stk,ps_sal,ps_pur,ps_ia,ps_studio,ps_product_manager,ps_pm,ps_cm, ps_fa, ps_er, ps_sw, ps_prc, ps_guide, ps_ap,
check_roles = True
load_odoo_module_menu = False
# 新建用户默认密码
default_user_pwd = Abc123456

# 创建时数据批量 insert 每次执行条数
# execute_values_size = 1000

# 开发环境 development 生产环境 production
# ps_env = production
# 工作流服务地址
ps_flowable_base_url = http://192.168.34.101:8888
# odoo应用服务地址，用于工作流回调odoo服务
ps_odoo_base_url = https://yangxingcai-13.app.mypscloud.com
# websocket地址
# 用于浏览器中通过js连接服务器
ps_socket_base_url = wss://xxx-robot.app.mypscloud.com:7001/wss/
# odoo移动端应用服务地址，用于移动端发送消息
ps_mobile_base_url = http://odoo.studio.insuite.cn

# 网络锁服务地址
ps_netcontrol_url = http://192.168.34.101:8888

server_wide_modules = web,queue_job,ps_studio,ps_websocket
;xmlrpc_port = 8070
# 运维管理平台服务地址
# operation_maintenance_url = https://xxx-upgrade.app.mypscloud.com


[queue_job]
channels = root:8,root.seq_generator:1,root.post_account_balance:1,root.post_cash_flow:1,root.update_voucher_state:1,root.lot_seq_generator:1,root.update_card_and_policy_balance:1,root.planning_operation:1,root.fa_depr_wizard:1
scheme = http
host = localhost
;port = 8070
http_auth_user = odoo
http_auth_password = s3cr3t
jobrunner_db_host =  yangxingcai_db
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

# 版本升级配置参数
[upgrade]
upgrade_version = 1.1.1-1.2.0

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