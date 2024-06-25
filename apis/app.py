from flask import Flask
from flask_restful import Resource, Api, reqparse
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc, func, text, MetaData, Table, create_engine, select
from sqlalchemy.orm import sessionmaker
import configparser
import datetime
from flask_cors import CORS
import re

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
api_config = config['api']
near_range = int(api_config['near_range'])
cors=api_config['cors']
app = Flask(__name__)
CORS(app,origins=cors.split(','))
api = Api(app)

# Configure your SQLAlchemy database URI here
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{user}:{password}@{host}:{port}/{database}'
db = SQLAlchemy(app)

class Versions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    language = db.Column(db.String(255))
    version = db.Column(db.String(255))
    run_date = db.Column(db.DateTime)

def Data(table_name):
    metadata = MetaData()
    metadata.bind = db.engine
    table = Table(table_name, metadata, autoload_with=db.engine)
    metadata.reflect(bind=db.engine)
    return table

def get_table_name(language, version):
    version_replaced = version.replace('.', '_')
    table_name = f"{language}_{version_replaced}"
    return table_name
def parse_query(query):
    # 解析查询字符串
    tokens = re.findall(r'(-?"[^"]+"|\S+)', query)
    search_terms = {
        "exact": [],
        "exclude": [],
        "language_specific": {},
        "filename": "",
        "expression": ""
    }
    for token in tokens:
        if token.startswith('-"') and token.endswith('"'):
            search_terms["exclude"].append(token[2:-1])
        elif token.startswith('"') and token.endswith('"'):
            search_terms["exact"].append(token[1:-1])
        elif token.startswith('-'):
            search_terms["exclude"].append(token[1:])
        elif ':' in token:
            key, value = token.split(':', 1)
            if key in ["cn", "en", "ja"]:
                if key not in search_terms["language_specific"]:
                    search_terms["language_specific"][key] = []
                search_terms["language_specific"][key].append(value)
            elif key == "filename":
                search_terms["filename"] = value
        elif token.startswith('(') and token.endswith(')'):
            search_terms["expression"] = token[1:-1]
        else:
            search_terms["exact"].append(token)
    return search_terms

def search_data(data, query):
    
    search_terms = parse_query(query)
    results = []
    for item in data:
        # 这里添加具体的搜索逻辑
        pass
    return results

def search_across_tables(data, lang_version_tables):
    queries = []
    for language, version, table_name in lang_version_tables:
        query = text(f"""
            SELECT id, name, data, path, MATCH (data) AGAINST (:data IN NATURAL LANGUAGE MODE) AS score
            FROM {table_name}
            WHERE MATCH (data) AGAINST (:data IN NATURAL LANGUAGE MODE)
        """)
        query_results = db.session.execute(query, {'data': data}).fetchall()
        
        # Add language and version to each result
        for result in query_results:
            queries.append({
                'id': result[0],
                'name': result[1],
                'data': result[2],
                'path': result[3],
                'score': result[4],
                'language': language,
                'version': version
            })

    # Sort by score in descending order
    queries.sort(key=lambda x: x['score'], reverse=True)
    return queries
def include_search_across_tables(data, lang_version_tables):
    queries = []
    for language, version, table_name in lang_version_tables:
        table = Data(table_name)
        stmt = select(table.c.id, table.c.name, table.c.data, table.c.path).where(table.c.data.like(f"%{data}%"))
        query_results = db.session.execute(stmt).fetchall()
        # Add language and version to each result
        for result in query_results:
            queries.append({
                'id': result.id,
                'name': result.name,
                'data': result.data,
                'path': result.path,
                'language': language,
                'version': version
            })
    return queries

def exact_search_across_tables(data, lang_version_tables):
    queries = []
    for language, version, table_name in lang_version_tables:
        table = Data(table_name)
        stmt = select(table.c.id, table.c.name, table.c.data, table.c.path).where(table.c.data==(f"{data}"))
        query_results = db.session.execute(stmt).fetchall()
        
        # Add language and version to each result
        for result in query_results:
            queries.append({
                'id': result.id,
                'name': result.name,
                'data': result.data,
                'path': result.path,
                'language': language,
                'version': version
            })
    return queries


class AllVersions(Resource):
    def get(self):
        versions = Versions.query.all()
        return [{'id': v.id, 'language': v.language, 'version': v.version , 'run_date': v.run_date.strftime("%Y-%m-%d %H:%M:%S")} for v in versions]
    
class AllLanguages(Resource):
    def get(self):
        languages = Versions.query.with_entities(Versions.language).distinct()
        return [lang.language for lang in languages]

class VersionsByLanguage(Resource):
    def get(self, language):
        versions = Versions.query.filter_by(language=language).all()
        return [v.version for v in versions]

class LatestVersionByLanguage(Resource):
    def get(self):
        latest_versions = db.session.query(Versions.language, func.max(Versions.version)).group_by(Versions.language).all()
        return [{lang: version} for lang, version in latest_versions]

class DataByData(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('data', required=True, location='args')
        parser.add_argument('language', required=True, location='args')
        parser.add_argument('version', required=True, location='args')
        # 添加分页参数
        parser.add_argument('page', type=int, required=False, default=1, location='args')
        parser.add_argument('per_page', type=int, required=False, default=10, location='args')
        args = parser.parse_args()

        table_name = get_table_name(args['language'], args['version'])
        data_table = Data(table_name)

        # 计算总数据量
        total = db.session.query(data_table).filter(text("MATCH (data) AGAINST (:data IN NATURAL LANGUAGE MODE)")).params(data=args['data']).count()

        # 修改查询以支持分页
        data = db.session.query(data_table).filter(text("MATCH (data) AGAINST (:data IN NATURAL LANGUAGE MODE)")).params(data=args['data']).paginate(page=args['page'], per_page=args['per_page'], error_out=False).items

        # 返回数据和分页信息
        return {
            'data': [{'id': d.id, 'name': d.name, 'data': d.data, 'path': d.path} for d in data],
            'pagination': {
                'page': args['page'],
                'per_page': args['per_page'],
                'total': total,
            }
        }

class MultiDataByData(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('data', required=True, location='args')
        parser.add_argument('language', required=True, location='args')
        parser.add_argument('version', required=True, location='args')
        parser.add_argument('languages', required=True, location='args')
        parser.add_argument('versions', required=True, location='args')
        args = parser.parse_args()
        languages = args['languages'].split(',')
        versions = args['versions'].split(',')
        table_name = get_table_name(args['language'], args['version'])
        data_table = Data(table_name)
        data = db.session.query(data_table).filter(text("MATCH (data) AGAINST (:data IN NATURAL LANGUAGE MODE)")).params(data=args['data']).all()
        initResults= [{'id': d.id, 'name': d.name, 'data': d.data, 'path': d.path} for d in data]
        results = []
                # 收集所有需要查询的路径和ID
        paths_ids = set((initresult['path'], initresult['id']) for initresult in initResults)
        # If there are no paths or ids to query, return early
        if not paths_ids:
            return []  # Or return a meaningful message
        # 构建查询映射
        data_mapping = {}
        for language, version in zip(languages, versions):
            table_name = get_table_name(language, version)
            data_table = Data(table_name)
            # 一次性查询所有相关数据
            all_data = db.session.query(data_table).filter(
    text("path IN :paths AND id IN :ids")
).params(
    paths=[path for path, _ in paths_ids],
    ids=[id for _, id in paths_ids]
).all()
            # 将查询结果存储在映射中
            for data in all_data:
                key = (data.path, data.id)
                if key not in data_mapping:
                    data_mapping[key] = []
                data_mapping[key].append({'language': language, 'version': version, 'data': data.data})

        # 使用映射填充结果
        results = []
        for initresult in initResults:
            key = (initresult['path'], initresult['id'])
            result_data = data_mapping.get(key, [{'language': language, 'version': version, 'data': f'Data not found for language {language} and version {version}'} for language, version in zip(languages, versions)])
            results.append({'id': initresult['id'], 'name': initresult['name'], 'data': initresult['data'], 'path': initresult['path'], 'data': result_data})

        return results
    
class MultiLanguagesDataByData(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('data', required=True, location='args')
        parser.add_argument('languages', required=True, location='args')
        parser.add_argument('versions', required=True, location='args')
        args = parser.parse_args()
        languages = args['languages'].split(',')
        versions = args['versions'].split(',')
        lang_version_tables = [(language, version, get_table_name(language, version)) for language, version in zip(languages, versions)]
        initresults = search_across_tables(args['data'], lang_version_tables)
        results = []
        # 收集所有需要查询的路径和ID
        paths_ids = set((initresult['path'], initresult['id']) for initresult in initresults)
        # If there are no paths or ids to query, return early
        if not paths_ids:
            return []  # Or return a meaningful message
        # 构建查询映射
        data_mapping = {}
        for language, version in zip(languages, versions):
            table_name = get_table_name(language, version)
            data_table = Data(table_name)
            # 一次性查询所有相关数据
            all_data = db.session.query(data_table).filter(
    text("path IN :paths AND id IN :ids")
).params(
    paths=[path for path, _ in paths_ids],
    ids=[id for _, id in paths_ids]
).all()
            # 将查询结果存储在映射中
            for data in all_data:
                key = (data.path, data.id)
                if key not in data_mapping:
                    data_mapping[key] = []
                data_mapping[key].append({'language': language, 'version': version, 'data': data.data})

        # 使用映射填充结果
        results = []
        for initresult in initresults:
            key = (initresult['path'], initresult['id'])
            result_data = data_mapping.get(key, [{'language': language, 'version': version, 'data': f'Data not found for language {language} and version {version}'} for language, version in zip(languages, versions)])
            results.append({'id': initresult['id'], 'name': initresult['name'], 'data': initresult['data'], 'path': initresult['path'], 'data': result_data})

        return results

class IncludeMultiDataByData(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('data', required=True, location='args')
        parser.add_argument('language', required=True, location='args')
        parser.add_argument('version', required=True, location='args')
        parser.add_argument('languages', required=True, location='args')
        parser.add_argument('versions', required=True, location='args')
        args = parser.parse_args()
        languages = args['languages'].split(',')
        versions = args['versions'].split(',')
        table_name = get_table_name(args['language'], args['version'])
        table = Data(table_name)
        stmt = select(table.c.id, table.c.name, table.c.data, table.c.path).where(table.c.data.like(f"%{args['data']}%"))
        data = db.session.execute(stmt).fetchall()
        initResults= [{'id': d.id, 'name': d.name, 'data': d.data, 'path': d.path} for d in data]
        results = []
                # 收集所有需要查询的路径和ID
        paths_ids = set((initresult['path'], initresult['id']) for initresult in initResults)
        # If there are no paths or ids to query, return early
        if not paths_ids:
            return []  # Or return a meaningful message
        # 构建查询映射
        data_mapping = {}
        for language, version in zip(languages, versions):
            table_name = get_table_name(language, version)
            data_table = Data(table_name)
            # 一次性查询所有相关数据
            all_data = db.session.query(data_table).filter(
    text("path IN :paths AND id IN :ids")
).params(
    paths=[path for path, _ in paths_ids],
    ids=[id for _, id in paths_ids]
).all()
            # 将查询结果存储在映射中
            for data in all_data:
                key = (data.path, data.id)
                if key not in data_mapping:
                    data_mapping[key] = []
                data_mapping[key].append({'language': language, 'version': version, 'data': data.data})

        # 使用映射填充结果
        results = []
        for initresult in initResults:
            key = (initresult['path'], initresult['id'])
            result_data = data_mapping.get(key, [{'language': language, 'version': version, 'data': f'Data not found for language {language} and version {version}'} for language, version in zip(languages, versions)])
            results.append({'id': initresult['id'], 'name': initresult['name'], 'data': initresult['data'], 'path': initresult['path'], 'data': result_data})

        return results

class IncludeMultiLanguagesDataByData(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('data', required=True, location='args')
        parser.add_argument('languages', required=True, location='args')
        parser.add_argument('versions', required=True, location='args')
        args = parser.parse_args()
        languages = args['languages'].split(',')
        versions = args['versions'].split(',')
        lang_version_tables = [(language, version, get_table_name(language, version)) for language, version in zip(languages, versions)]
        initresults = include_search_across_tables(args['data'], lang_version_tables)
        results = []
        # 收集所有需要查询的路径和ID
        paths_ids = set((initresult['path'], initresult['id']) for initresult in initresults)
        # If there are no paths or ids to query, return early
        if not paths_ids:
            return []  # Or return a meaningful message
        # 构建查询映射
        data_mapping = {}
        for language, version in zip(languages, versions):
            table_name = get_table_name(language, version)
            data_table = Data(table_name)
            # 一次性查询所有相关数据
            all_data = db.session.query(data_table).filter(
    text("path IN :paths AND id IN :ids")
).params(
    paths=[path for path, _ in paths_ids],
    ids=[id for _, id in paths_ids]
).all()
            # 将查询结果存储在映射中
            for data in all_data:
                key = (data.path, data.id)
                if key not in data_mapping:
                    data_mapping[key] = []
                data_mapping[key].append({'language': language, 'version': version, 'data': data.data})

        # 使用映射填充结果
        results = []
        for initresult in initresults:
            key = (initresult['path'], initresult['id'])
            result_data = data_mapping.get(key, [{'language': language, 'version': version, 'data': f'Data not found for language {language} and version {version}'} for language, version in zip(languages, versions)])
            results.append({'id': initresult['id'], 'name': initresult['name'], 'data': initresult['data'], 'path': initresult['path'], 'data': result_data})

        return results
    
class ExactMultiDataByData(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('data', required=True, location='args')
        parser.add_argument('language', required=True, location='args')
        parser.add_argument('version', required=True, location='args')
        parser.add_argument('languages', required=True, location='args')
        parser.add_argument('versions', required=True, location='args')
        args = parser.parse_args()
        languages = args['languages'].split(',')
        versions = args['versions'].split(',')
        table_name = get_table_name(args['language'], args['version'])
        table = Data(table_name)
        stmt = select(table.c.id, table.c.name, table.c.data, table.c.path).where(table.c.data==(f"{args['data']}"))
        data = db.session.execute(stmt).fetchall()
        initResults= [{'id': d.id, 'name': d.name, 'data': d.data, 'path': d.path} for d in data]
        results = []
                # 收集所有需要查询的路径和ID
        paths_ids = set((initresult['path'], initresult['id']) for initresult in initResults)
        # If there are no paths or ids to query, return early
        if not paths_ids:
            return []  # Or return a meaningful message
        # 构建查询映射
        data_mapping = {}
        for language, version in zip(languages, versions):
            table_name = get_table_name(language, version)
            data_table = Data(table_name)
            # 一次性查询所有相关数据
            all_data = db.session.query(data_table).filter(
    text("path IN :paths AND id IN :ids")
).params(
    paths=[path for path, _ in paths_ids],
    ids=[id for _, id in paths_ids]
).all()
            # 将查询结果存储在映射中
            for data in all_data:
                key = (data.path, data.id)
                if key not in data_mapping:
                    data_mapping[key] = []
                data_mapping[key].append({'language': language, 'version': version, 'data': data.data})

        # 使用映射填充结果
        results = []
        for initresult in initResults:
            key = (initresult['path'], initresult['id'])
            result_data = data_mapping.get(key, [{'language': language, 'version': version, 'data': f'Data not found for language {language} and version {version}'} for language, version in zip(languages, versions)])
            results.append({'id': initresult['id'], 'name': initresult['name'], 'data': initresult['data'], 'path': initresult['path'], 'data': result_data})

        return results
    
class ExactMultiLanguagesDataByData(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('data', required=True, location='args')
        parser.add_argument('languages', required=True, location='args')
        parser.add_argument('versions', required=True, location='args')
        args = parser.parse_args()
        languages = args['languages'].split(',')
        versions = args['versions'].split(',')
        lang_version_tables = [(language, version, get_table_name(language, version)) for language, version in zip(languages, versions)]
        initresults = exact_search_across_tables(args['data'], lang_version_tables)
        results = []
                # 收集所有需要查询的路径和ID
        paths_ids = set((initresult['path'], initresult['id']) for initresult in initresults)
        # If there are no paths or ids to query, return early
        if not paths_ids:
            return []  # Or return a meaningful message
        # 构建查询映射
        data_mapping = {}
        for language, version in zip(languages, versions):
            table_name = get_table_name(language, version)
            data_table = Data(table_name)
            # 一次性查询所有相关数据
            all_data = db.session.query(data_table).filter(
    text("path IN :paths AND id IN :ids")
).params(
    paths=[path for path, _ in paths_ids],
    ids=[id for _, id in paths_ids]
).all()
            # 将查询结果存储在映射中
            for data in all_data:
                key = (data.path, data.id)
                if key not in data_mapping:
                    data_mapping[key] = []
                data_mapping[key].append({'language': language, 'version': version, 'data': data.data})

        # 使用映射填充结果
        results = []
        for initresult in initresults:
            key = (initresult['path'], initresult['id'])
            result_data = data_mapping.get(key, [{'language': language, 'version': version, 'data': f'Data not found for language {language} and version {version}'} for language, version in zip(languages, versions)])
            results.append({'id': initresult['id'], 'name': initresult['name'], 'data': initresult['data'], 'path': initresult['path'], 'data': result_data})

        return results
    
class DataByPath(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('path', required=True, location='args')
        parser.add_argument('language', required=True, location='args')
        parser.add_argument('version', required=True, location='args')
        args = parser.parse_args()
        table_name = get_table_name(args['language'], args['version'])
        data_table = Data(table_name)
        data = db.session.query(data_table).filter_by(path=args['path']).all()
        if data:
            return [{'id': d.id, 'name': d.name, 'data': d.data, 'path': d.path} for d in data]
        else:
            return {'error': 'Data not found'}, 404

class DataAroundPathAndId(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('path', required=True, location='args')
        parser.add_argument('id', required=True, type=int, location='args')  # Ensure 'id' is an integer
        parser.add_argument('language', required=True, location='args')
        parser.add_argument('version', required=True, location='args')
        parser.add_argument('near_range', required=False, type=int, location='args')
        args = parser.parse_args()
        table_name = get_table_name(args['language'], args['version'])
        data_table = Data(table_name)
        data = db.session.query(data_table).filter_by(id=args['id'], path=args['path']).first()
        results = []
        if data:
            data_around = db.session.query(data_table).filter_by(path=args['path']).all()
            data_index = data_around.index(data)
            near_range = args['near_range'] if args['near_range'] else near_range
            start = max(0, data_index - near_range)
            end = data_index + near_range + 1
            results = [{'id': d.id, 'name': d.name, 'data': d.data, 'path': d.path} for d in data_around[start:end]]
        else:
            results.append({'error': f'Data not found'})
        return results
        
class MultiLanguagesDataByPathAndId(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('path', required=True, location='args')
        parser.add_argument('id', required=True, location='args')
        parser.add_argument('languages', required=True, location='args')
        parser.add_argument('versions', required=True, location='args')
        args = parser.parse_args()
        languages = args['languages'].split(',')
        versions = args['versions'].split(',')
        results = []
        for language, version in zip(languages, versions):
            table_name = get_table_name(language, version)
            data_table = Data(table_name)
            data = db.session.query(data_table).filter_by(path=args['path'], id=args['id']).first()
            if data:
                results.append({'language':language,'version':version,'id': data.id, 'name': data.name, 'data': data.data, 'path': data.path})
            else:
                results.append({'error': f'Data not found for language {language} and version {version}'})
        return results

class MultiLanguagesDataAroundName(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name', required=True, location='args')
        parser.add_argument('languages', required=True, location='args')
        parser.add_argument('versions', required=True, location='args')
        parser.add_argument('near_range', required=False, type=int, location='args')
        args = parser.parse_args()
        languages = args['languages'].split(',')
        versions = args['versions'].split(',')
        results = []
        print(near_range)
        nearrange = args['near_range'] if args['near_range'] else near_range
        for language, version in zip(languages, versions):
            table_name = get_table_name(language, version)
            data_table = Data(table_name)
            data = db.session.query(data_table).filter_by(name=args['name']).first()
            if data:
                start_index = max(0, data.id - nearrange)
                end_index = data.id + nearrange

                sql_query = text(f"""
SELECT * FROM (
    SELECT *
    FROM {table_name}
    WHERE path = :path
) AS numbered_rows
WHERE id BETWEEN :start_index AND :end_index
""")

                # 使用SQLAlchemy执行这个查询
                data_around = db.session.execute(sql_query, {'path': data.path, 'start_index': start_index, 'end_index': end_index}).fetchall()

                #data_around = db.session.query(data_table).filter_by(path=data.path).all()
                #data_index = data_around.index(data)
                
                #start = max(0, data_index - nearrange)
                #end = data_index + nearrange + 1
                results.append({'language':language,'version':version,'data':[{'id': d.id, 'name': d.name, 'data': d.data, 'path': d.path} for d in data_around]})
            else:
                results.append({'error': f'Data not found for language {language} and version {version}'})
        if not results:
            results.append({'error': f'Data not found for any language and version'})
        results_by_id = {}
        for entry in results:
            if 'error' in entry:
                continue
            language = entry['language']
            version = entry['version']
            for data_item in entry['data']:
                item_id = data_item['id']
                if item_id not in results_by_id:
                    results_by_id[item_id] = {
                        'id': item_id,
                        'name': data_item['name'],
                        'data': [],
                        'path': data_item['path']
                    }
                results_by_id[item_id]['data'].append({
                    'language': language,
                    'version': version,
                    'data': data_item['data']
                })
        return list(results_by_id.values())
    

api.add_resource(AllVersions, '/versions')
api.add_resource(AllLanguages, '/languages')
api.add_resource(VersionsByLanguage, '/versions/<string:language>')
api.add_resource(LatestVersionByLanguage, '/latest_versions')
api.add_resource(DataByData, '/data_by_data')
api.add_resource(MultiDataByData, '/multi_data_by_data')
api.add_resource(MultiLanguagesDataByData, '/multi_language_data_by_data')
api.add_resource(IncludeMultiDataByData, '/include_multi_data_by_data')
api.add_resource(IncludeMultiLanguagesDataByData, '/include_multi_language_data_by_data')
api.add_resource(ExactMultiDataByData, '/exact_multi_data_by_data')
api.add_resource(ExactMultiLanguagesDataByData, '/exact_multi_language_data_by_data')
api.add_resource(DataByPath, '/data_by_path')
api.add_resource(DataAroundPathAndId, '/data_around_path_and_id')
api.add_resource(MultiLanguagesDataByPathAndId, '/multi_language_data_by_path_and_id')
api.add_resource(MultiLanguagesDataAroundName, '/multi_language_data_around_name')

if __name__ == '__main__':
    app.run(debug=True)
