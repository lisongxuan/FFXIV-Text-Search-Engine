import os
import csv
import pymysql
import configparser
import datetime

# 读取配置文件
config = configparser.ConfigParser()
config.read('config.txt')
# 获取数据库配置
db_config = config['database']
host = db_config['host']
port = int(db_config['port'])  # 端口号需要转换为整数
user = db_config['user']
password = db_config['password']
database = db_config['database']

# 获取用户输入的语言
language = input("请输入语言：")

# 获取用户输入的版本号
version = input("请输入版本号：")

# 将版本号中的小数点替换为下划线
versionReplaced = version.replace('.', '_')

# 获取用户输入的目录地址
directory = os.path.normpath(input("请输入目录地址："))

# 连接到MySQL数据库
db = pymysql.connect(host=host, user=user, password=password, database=database, port=port)
cursor = db.cursor()

# 使用语言和版本号共同构成表名
table_name = f"{language}_{versionReplaced}"

# 检查表是否存在，如果不存在则创建
cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
if cursor.fetchone() is None:
    cursor.execute(f"""
    CREATE TABLE {table_name} (
        id INT,
        name VARCHAR(255),
        data LONGTEXT,
        path VARCHAR(255),
        PRIMARY KEY (id, path)
    )
    """)
sql = f"ALTER TABLE {table_name} ADD FULLTEXT(data)"
cursor.execute(sql)

cursor.execute("SHOW TABLES LIKE 'versions'")
if cursor.fetchone() is None:
    cursor.execute("""
    CREATE TABLE versions (
        id INT AUTO_INCREMENT,
        language VARCHAR(255),
        version VARCHAR(255),
        run_date DATETIME,
        PRIMARY KEY (id)
    )
    """)

# 从数据库的folders表中查询出所有需要读取的目录名
cursor.execute("SELECT folder_name FROM folders")
folders_to_process = [row[0] for row in cursor.fetchall()]
print(f"需要处理的目录有：{folders_to_process}")

# 定义一个函数来遍历目录和子目录
# 定义一个函数来遍历目录和子目录
def process_files(directory):
    for foldername, subfolders, filenames in os.walk(directory):
        if any(foldername.startswith(os.path.join(directory, folder)) for folder in folders_to_process):
            for filename in filenames:
                if filename.endswith('.csv'):
                    filepath = os.path.join(foldername, filename)
                    relpath = os.path.relpath(filepath, directory)  # 获取文件的相对路径
                    with open(filepath, 'r', encoding='utf-8') as f:
                        csv_reader = csv.reader(f)
                        # 跳过前三行
                        for _ in range(3):
                            next(csv_reader)
                        for row in csv_reader:
                            try:
                                id = int(row[0])  # 尝试将id转换为整数
                            except ValueError:
                                print(f"Invalid id {row[0]} in file {relpath}, skipping this row.")
                                continue
                            name = row[1]
                            data = row[2]
                            # 如果data字段为空，则跳过这一行
                            if not data:
                                continue
                            # 插入一条记录到数据库，如果主键重复则忽略
                            sql = f"INSERT IGNORE INTO {table_name} (id, name, data, path) VALUES (%s, %s, %s, %s)"
                            cursor.execute(sql, (id, name, data, relpath))  # 使用相对路径
                    print(f"File {relpath} has been processed.")  # 每读取一个文件输出一条日志
            # 提交到数据库执行
            db.commit()
            print(f"Directory {foldername} has been processed and committed to the database.")  # 每遍历一个目录提交一次数据库并输出一条日志
# 遍历目录和子目录
process_files(directory)
# 在versions表中插入一条记录
sql = "INSERT INTO versions (language, version, run_date) VALUES (%s, %s, %s)"
now = datetime.datetime.now()
cursor.execute(sql, (language, version, now))
db.commit()

# 关闭数据库连接
db.close()