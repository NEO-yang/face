[options]
admin_passwd = admin
db_host = yangxingcai13_db
db_port = 5432
db_user = odoo 
db_password = I2iKYzd1qYWU7d7Oyxc
limit_time_real = 3000
create_profile_test_data = True
# db_name = 122103

# 使用redis生成最大编码
redis_code_rule_enable = True
redis_host = 192.168.34.101
redis_port = 6379
redis_password = 123456
redis_db = 1
redis_db_robot= 15
redis_max_conn = 100
redis_type = single

# 根据addons_path进行修改配置
base_src_dir = /opt/odoo
addons_path = /opt/odoo/core/addons,/opt/odoo/core/odoo/addons,/opt/odoo/sys,/opt/odoo/platform,/opt/odoo/fin,/opt/odoo/scm,/opt/odoo/ma,/opt/odoo/mfg,/opt/odoo/third-party/OCA-connector,/opt/odoo/third-party/OCA-queue,/opt/odoo/cost,/opt/odoo/tax,/opt/odoo/qm
check_roles = True
load_odoo_module_menu = False

# 创建时数据批量 insert 每次执行条数
# execute_values_size = 1000

# 开发环境 development 生产环境 production
# ps_env = production
ps_env = development
# 工作流服务地址
ps_flowable_base_url = http://192.168.34.101:8080
# odoo应用服务地址，用于工作流回调odoo服务
ps_odoo_base_url = https://yangxingcai-13.app.mypscloud.com
# 网络锁服务地址
ps_netcontrol_url = http://192.168.34.101:8081/odoo

server_wide_modules = web,queue_job,ps_studio
;xmlrpc_port = 8070
limit_memory_soft = 3221225472


[queue_job]
channels = root:4,root.seq_generator:1,root.post_account_balance:1,root.post_cash_flow:1,root.update_voucher_state:1,root.lot_seq_generator:1
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
[websocket]
ws_host = 127.0.0.1
ws_port = 7001